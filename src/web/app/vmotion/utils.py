# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# comment
#
# 16-8-3 qinjinghui : Init

import time
import logging
import random
import traceback
import datetime
import json
from voluptuous import Schema, Required, All, Length, Range, Invalid

from threading import Thread
from .. import db
from .. import app
from flask import current_app
from ..models import Desktop, DesktopType, DesktopState,\
    DesktopTask, TaskAction, TaskResult, TaskState, User
from .. import celery_tasks
from phoenix.cloud.admin import compute as OpenstackComputeService
from phoenix.cloud import image as OpenstackImageService
import heapq

LOG = logging.getLogger(__name__)


def migrate_desktop(vm_ref, destination_host):
    try:
        desktop = Desktop.query.filter_by(vm_ref=vm_ref).first()
        desktop.desktop_state = DesktopState.MIGRATING
        db.session.add(desktop)
        db.session.commit()

        vm = OpenstackComputeService.get_server(desktop.vm_ref)

        # Add Migrate Desktop Task
        migrate_desktop_task = DesktopTask()
        migrate_desktop_task.state = 'PENDING'
        migrate_desktop_task.action = TaskAction.MIGRATE
        migrate_desktop_task.stage_chain = json.dumps(['MIGRATE', 'WAIT','DETECT'])
        migrate_desktop_task.stage = 'MIGRATE'
        migrate_desktop_task.context = json.dumps({
            'course_name': desktop.course.name if desktop.course else None,
            'serial': desktop.name.split('_')[-1] if desktop.course else None,
            'desktop': desktop.id,
            'wait_state': 'ACTIVE',
            'wait_timeout': 10 * 60,
            'desktop_state_map': {'SUCCESS': 'ACTIVE', 'ERROR': 'ERROR'},
            'detect_method': 'PING',
            'detect_timeout': 30,
            'floating_ip': desktop.floating_ip,
            'source_host':vm.__dict__['OS-EXT-SRV-ATTR:host'],
            'destination_host': destination_host,
        })
        db.session.add(migrate_desktop_task)
        db.session.commit()

        celery_tasks.run_migrationtask(task_id=migrate_desktop_task.id,
                                     link=celery_tasks._create_desktop_detect.s(
                                         task_id=migrate_desktop_task.id),
                                     link_error=celery_tasks._create_desktop_detect.s(
                                         task_id=migrate_desktop_task.id))
        return True
    except Exception as ex:
        LOG.exception("Migrate VM Failed: %s" % vm_ref)
        return False



def evacuate_desktop(vm_ref, destination_host):
    try:
        desktop = Desktop.query.filter_by(vm_ref=vm_ref).first()
        desktop.desktop_state = DesktopState.EVACUATING
        db.session.add(desktop)
        db.session.commit()

        vm = OpenstackComputeService.get_server(desktop.vm_ref)

        # Add Evacuate Desktop Task
        evacuate_desktop_task = DesktopTask()
        evacuate_desktop_task.state = 'PENDING'
        evacuate_desktop_task.action = TaskAction.EVACUATE
        evacuate_desktop_task.stage_chain = json.dumps(['EVACUATE', 'WAIT', 'DISASSOCIATE', 'FLOATING', 'DETECT'])
        evacuate_desktop_task.stage = 'EVACUATE'
        evacuate_desktop_task.context = json.dumps({
            'course_name': desktop.course.name if desktop.course else None,
            'serial': desktop.name.split('_')[-1] if desktop.course else None,
            'desktop': desktop.id,
            'wait_state': 'ACTIVE',
            'wait_timeout': 10 * 60,
            'desktop_state_map': {'SUCCESS': 'ACTIVE', 'ERROR': 'ERROR'},
            'detect_method': 'PING',
            'detect_timeout': 30,
            'floating_ip': desktop.floating_ip,
            'source_host':vm.__dict__['OS-EXT-SRV-ATTR:host'],
            'destination_host': destination_host,
        })
        db.session.add(evacuate_desktop_task)
        db.session.commit()

        celery_tasks.run_migrationtask(task_id=evacuate_desktop_task.id,
                                     link=celery_tasks._create_desktop_detect.s(
                                         task_id=evacuate_desktop_task.id),
                                     link_error=celery_tasks._create_desktop_detect.s(
                                         task_id=evacuate_desktop_task.id))
        return True
    except:
        LOG.exception("Migrate VM Failed: %s" % vm_ref)
        return False


def evacuate_vms_to_active_hosts(src_host_name,dest_host_list, vm_list=None):
    if not vm_list:
        #Get VM list of src_host_name
        temp_vm_list = OpenstackComputeService.list_servers(search_opts={"host":src_host_name})
        vm_list = []
        for vm in temp_vm_list:
            if vm.status != "ERROR":
                vm_list.append(vm)
        if len(vm_list) == 0:
            return

    flavor_list = OpenstackComputeService.list_flavors()
    flavor_dict = {}
    for flavor in flavor_list:
        flavor_dict[flavor.id] = flavor

    #建立虚拟机与flavor的字典以方便后面查找
    vm_flavor_dict = {}
    for vm in vm_list:
        vm_flavor_dict[vm.id] = flavor_dict[vm.flavor['id']]

    #构建可用主机的可用内存最大堆
    dest_host_free_mem_max_heap = []
    for host in dest_host_list:
        heapq.heappush(dest_host_free_mem_max_heap,(int(host.mem_used)-int(host.mem), host.host_name))

    #创建撤离任务
    fail_vm_list = [] #记录那些内存不能满足的虚拟机
    for vm in vm_list:
        selected_host = heapq.heappop(dest_host_free_mem_max_heap)
        host_name = selected_host[1]
        free_mem = 0 - selected_host[0]
        if free_mem < vm_flavor_dict[vm.id].ram:
            fail_vm_list.append(vm)
            LOG.warning('[A]free_mem %s less than %s' % (free_mem, vm_flavor_dict[vm.id].ram))
            heapq.heappush(dest_host_free_mem_max_heap,selected_host)
            continue
        else:
            desktop = Desktop.query.filter_by(vm_ref=vm.id).first()
            if not desktop:
                heapq.heappush(dest_host_free_mem_max_heap,selected_host)
                continue
            else:
                if evacuate_desktop(desktop.vm_ref,host_name):
                    free_mem = free_mem - vm_flavor_dict[vm.id].ram
                    free_mem = 0 - free_mem
                    heapq.heappush(dest_host_free_mem_max_heap,(free_mem,host_name))
                else:
                    LOG.warning('[B]evacuate desktop fail')
                    fail_vm_list.append(vm)
                    heapq.heappush(dest_host_free_mem_max_heap, selected_host)

    return fail_vm_list


def migrate_vms_to_active_hosts(src_host_name,dest_host_list, vm_list=None):
    if not vm_list:
        #Get VM list of src_host_name
        temp_vm_list = OpenstackComputeService.list_servers(search_opts={"host":src_host_name})
        vm_list = []
        for vm in temp_vm_list:
            if vm.status != "ERROR":
                vm_list.append(vm)
        if len(vm_list) == 0:
            return

    flavor_list = OpenstackComputeService.list_flavors()
    flavor_dict = {}
    for flavor in flavor_list:
        flavor_dict[flavor.id] = flavor

    #建立虚拟机与flavor的字典以方便后面查找
    vm_flavor_dict = {}
    for vm in vm_list:
        vm_flavor_dict[vm.id] = flavor_dict[vm.flavor['id']]

    #构建可用主机的可用内存最大堆
    dest_host_free_mem_max_heap = []
    for host in dest_host_list:
        heapq.heappush(dest_host_free_mem_max_heap,(int(host.mem_used)-int(host.mem), host.host_name))

    #创建撤离任务
    fail_vm_list = [] #记录那些内存不能满足的虚拟机
    for vm in vm_list:
        selected_host = heapq.heappop(dest_host_free_mem_max_heap)
        host_name = selected_host[1]
        free_mem = 0 - selected_host[0]
        if free_mem < vm_flavor_dict[vm.id].ram:
            fail_vm_list.append(vm)
            heapq.heappush(dest_host_free_mem_max_heap,selected_host)
            continue
        else:
            desktop = Desktop.query.filter_by(vm_ref=vm.id).first()
            if not desktop:
                heapq.heappush(dest_host_free_mem_max_heap,selected_host)
                continue
            else:
                if migrate_desktop(desktop.vm_ref,host_name):
                    free_mem = free_mem - vm_flavor_dict[vm.id].ram
                    free_mem = 0 - free_mem
                    heapq.heappush(dest_host_free_mem_max_heap,(free_mem,host_name))
                else:
                    heapq.heappush(dest_host_free_mem_max_heap, selected_host)
    return fail_vm_list