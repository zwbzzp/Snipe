# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# comment
#
# 2016/4/14 qinjinghui : Init
__author__ = 'qinjinghui'

import time
import logging
import random
import traceback
import datetime
import json
import xlrd
from voluptuous import Schema, Required, All, Length, Range, Invalid

from threading import Thread
from ... import db
from ... import app
from flask import current_app
from ...models import Desktop, DesktopType, DesktopState,\
    DesktopTask, TaskAction, TaskResult, TaskState, User
from ... import celery_tasks
from flask.ext import excel
import pyexcel.ext.xls
import pyexcel.ext.xlsx
from phoenix.cloud import compute as OpenstackComputeService
from phoenix.cloud import image as OpenstackImageService

LOG = logging.getLogger(__name__)


def reboot_vm(vmid):
    try:
        desktop = Desktop.query.filter_by(vm_ref=vmid).first()
        desktop.desktop_state = DesktopState.REBOOTING
        db.session.add(desktop)
        db.session.commit()

        # Add Reboot Desktop Task
        reboot_desktop_task = DesktopTask()
        reboot_desktop_task.state = 'PENDING'
        reboot_desktop_task.action = TaskAction.REBOOT
        reboot_desktop_task.stage_chain = json.dumps(['REBOOT', 'WAIT','DETECT'])
        reboot_desktop_task.stage = 'REBOOT'
        reboot_desktop_task.context = json.dumps({
            'course_name': desktop.course.name if desktop.course else None,
            'serial': desktop.name.split('_')[-1] if desktop.course else None,
            'desktop': desktop.id,
            'wait_state': 'ACTIVE',
            'wait_timeout': 10 * 60,
            'desktop_state_map': {'SUCCESS': 'ACTIVE', 'ERROR': 'ERROR'},
            'detect_method': 'PING',
            'detect_timeout': 30,
            'floating_ip': desktop.floating_ip,
        })
        db.session.add(reboot_desktop_task)
        db.session.commit()

        celery_tasks.run_desktoptask(task_id=reboot_desktop_task.id,
                                     link=celery_tasks._create_desktop_detect.s(
                                         task_id=reboot_desktop_task.id),
                                     link_error=celery_tasks._create_desktop_detect.s(
                                         task_id=reboot_desktop_task.id))
        return True
    except:
        LOG.exception("Reboot VM Failed: %s" % vmid)
        return False


def suspend_vm(vmid):
    try:
        desktop = Desktop.query.filter_by(vm_ref=vmid).first()
        desktop.desktop_state = DesktopState.SUSPENDING
        db.session.add(desktop)
        db.session.commit()

        # Add Suspend Desktop Task
        suspend_desktop_task = DesktopTask()
        suspend_desktop_task.state = 'PENDING'
        suspend_desktop_task.action = TaskAction.STOP
        suspend_desktop_task.stage_chain = json.dumps(
            ['SUSPEND', 'WAIT'])
        suspend_desktop_task.stage = 'SUSPEND'
        suspend_desktop_task.context = json.dumps({
            'course_name':desktop.course.name if desktop.course else None,
            'serial': desktop.name.split('_')[-1] if desktop.course else None,
            'desktop': desktop.id,
            'wait_state': 'SUSPENDED',
            'wait_timeout': 10 * 60,
            'desktop_state_map': {'SUCCESS': 'SUSPENDED', 'ERROR': 'ERROR'}
        })
        db.session.add(suspend_desktop_task)
        db.session.commit()

        celery_tasks.run_desktoptask(task_id=suspend_desktop_task.id)
        return True
    except:
        LOG.exception("Suspend VM Failed: %s" % vmid)
        return False


def resume_vm(vmid):
    try:
        desktop = Desktop.query.filter_by(vm_ref=vmid).first()
        desktop.desktop_state = DesktopState.STARTING
        db.session.add(desktop)
        db.session.commit()

        # Add Resume Desktop Task
        resume_desktop_task = DesktopTask()
        resume_desktop_task.state = 'PENDING'
        resume_desktop_task.action = TaskAction.RESUME
        resume_desktop_task.stage_chain = json.dumps(
            ['RESUME', 'WAIT','DETECT'])
        resume_desktop_task.stage = 'RESUME'
        resume_desktop_task.context = json.dumps({
            'course_name': desktop.course.name if desktop.course else None,
            'serial': desktop.name.split('_')[-1] if desktop.course else None,
            'desktop': desktop.id,
            'wait_state': 'ACTIVE',
            'wait_timeout': 10 * 60,
            'desktop_state_map': {'SUCCESS': 'ACTIVE', 'ERROR': 'ERROR'},
            'detect_method': 'PING',
            'detect_timeout': 30,
            'floating_ip': desktop.floating_ip,
        })
        db.session.add(resume_desktop_task)
        db.session.commit()

        celery_tasks.run_desktoptask(task_id=resume_desktop_task.id)
        return True
    except:
        LOG.error("Resume VM Failed: %s" % vmid)
        return False


def rebuild_vm(vmid):
    try:
        desktop = Desktop.query.filter_by(vm_ref=vmid).first()
        desktop.desktop_state = DesktopState.REBUILDING
        db.session.add(desktop)
        db.session.commit()

        # Add Rebuild Desktop Task
        rebuild_desktop_task = DesktopTask()
        rebuild_desktop_task.state = 'PENDING'
        rebuild_desktop_task.action = TaskAction.REBUILD
        rebuild_desktop_task.stage_chain = json.dumps(
            ['REBUILD', 'WAIT', 'DETECT'])
        rebuild_desktop_task.stage = 'REBUILD'
        rebuild_desktop_task.context = json.dumps({
            'course_name': desktop.course.name if desktop.course else None,
            'serial': desktop.name.split('_')[-1] if desktop.course else None,
            'desktop': desktop.id,
            'image':desktop.image_ref,
            'wait_state': 'ACTIVE',
            'wait_timeout': 10 * 60,
            'desktop_state_map': {'SUCCESS': 'ACTIVE', 'ERROR': 'ERROR'},
            'detect_method': 'PING',
            'detect_timeout': 30,
            'floating_ip': desktop.floating_ip,
        })
        db.session.add(rebuild_desktop_task)
        db.session.commit()

        celery_tasks.run_desktoptask(task_id=rebuild_desktop_task.id,
                                     link=celery_tasks._create_desktop_detect.s(
                                         task_id=rebuild_desktop_task.id),
                                     link_error=celery_tasks._create_desktop_detect.s(
                                         task_id=rebuild_desktop_task.id))
        return True
    except:
        LOG.exception("Rebuild VM Failed: %s" % vmid)
        return False


def change_time_to_datetime(time):
    """
    Change time object to datetime object
    """
    today = datetime.date.today()
    newdatetime = datetime.datetime.combine(today, time)
    return newdatetime


def create_static_vm(owner_id, image_id,flavor_id, network_ref):
    try:
        image = OpenstackImageService.get_image(image_id)
        user = User.query.filter_by(username=owner_id).first()
        user_id = user.id
        serial = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        desktop_name = owner_id + '_' + image.name + '_' + str(serial)
        desktop = Desktop()
        desktop.name = desktop_name
        desktop.vm_ref = None
        desktop.desktop_type = DesktopType.STATIC
        desktop.start_datetime = datetime.datetime.now()
        desktop.end_datetime = datetime.datetime(3016, 1, 1, 0, 0, 0, 1)
        desktop.desktop_state = DesktopState.BUILD
        desktop.owner_id = user_id
        desktop.image_ref = image_id
        desktop.flavor_ref = flavor_id
        db.session.add(desktop)
        db.session.commit()
        #Add Create Instance Task
        create_instance_task = DesktopTask()
        create_instance_task.state = 'PENDING'
        create_instance_task.stage_chain = json.dumps(['BUILD', 'WAIT', 'FLOATING', 'DETECT'])
        create_instance_task.stage = 'BUILD'
        create_instance_task.context = json.dumps({
            'course': None,
            'serial': None,
            'desktop': desktop.id,
            'desktop_name': desktop_name,
            "owner": user_id,
            "desktop_type": DesktopType.STATIC,
            'start_datetime': datetime.datetime.now().isoformat(),
            'end_datetime': datetime.datetime(3016, 1, 1, 0, 0, 0, 1).isoformat(),#'3016-01-01T19:33:23.185419',
            'flavor': flavor_id,
            'image': image_id,
            'network': network_ref,
            'subnet': None,
            'port': None,
            'disk': None,
            'wait_state': 'ACTIVE',
            'wait_timeout': 10*60,
            'floating_action': 'ASSIGN',
            'detect_method': 'PING',
            'detect_timeout': 30,
        })
        db.session.add(create_instance_task)
        db.session.commit()

        celery_tasks.run_desktoptask(task_id=create_instance_task.id,
                                     link=celery_tasks._create_desktop_detect.s(task_id=create_instance_task.id),
                                     link_error=celery_tasks._create_desktop_detect.s(task_id=create_instance_task.id))

        return True, desktop_name
    except:
        LOG.exception('Create VM Instance Failed: %s %s %s' % (owner_id, image_id,flavor_id))
        return False, ""


def delete_vm(vmid):
    try:
        # Add Delete Instance Task
        desktop = Desktop.query.filter_by(vm_ref=vmid).first()
        if desktop.vm_state == DesktopState.DELETING:
            return "success"
        delete_instance_task = DesktopTask()
        delete_instance_task.state = 'PENDING'
        delete_instance_task.stage_chain = json.dumps(['DELETE'])
        delete_instance_task.stage = 'DELETE'
        delete_instance_task.context = json.dumps({
            'course_name': desktop.course.name if desktop.course else None,
            'serial': desktop.name.split('_')[-1] if desktop.course else None,
            'vm': vmid,
            'desktop': desktop.id
        })
        desktop.desktop_state = 'DELETING'
        db.session.add(desktop)
        db.session.add(delete_instance_task)
        db.session.commit()
        celery_tasks.run_desktoptask(delete_instance_task.id)
        return "success"
    except:
        LOG.exception('Delete vm desktop %s failed' % vmid)

        return "error"


def judge_file(file, size):
    '''
    To judge whether the file is valid.
    @param file: the file object
    @param size: the size(MB) of the limit of the file.
    '''
    try:
        if file and size:
            if file.content_length > (size * 1024 * 1024):
                return False, "too large"
            temp = file.filename.split(".")
            file_type = temp[len(temp) - 1]
            if file_type == "xls" or file_type == "xlsx":
                return True, ""
            else:
                return False,"type error"
        else:
            raise "Invalid parameter"
    except:
        LOG.exception("Check file %s failed" % file.filename)
        return False, ""


def add_fail_info(fail_list, userid, templateid, flavor, msg="something wrong"):
    user = {'userid': userid, "template": templateid, "flavor": flavor, 'info': msg}
    fail_list.append(user)


def check_image_flavor_is_existed(imageid, flavorid):
    '''
    '''
    try:
        flavor = OpenstackComputeService.get_flavor(flavorid)
        image = OpenstackImageService.get_image(imageid)
        if flavor and image:
            return True
    except:
        LOG.exception("Check image id %s flavor id %s existed failed" % (imageid, flavorid))
    return False


#########################
# parameter validate
#########################

# helper methods
def Date(fmt='%Y/%m/%d'):
    return lambda v: datetime.datetime.strptime(v, fmt)


def Int():
    def is_int(v):
        try:
            int(v)
        except Exception as e:
            raise Invalid('not integer')
    return is_int


def PostiveInt():
    def is_positive_int(v):
        try:
            int(v)
            if v <= 0:
                raise Exception()
        except Exception as e:
            raise Invalid('not positive integer')
    return is_positive_int


class DesktopCountValidator():

    # define parameter validators here
    def __init__(self):
        self.schema = Schema({
            'count': All(PostiveInt())
        })

    def validate(self, value):
        try:
            self.schema({'count': value})
            return True
        except Invalid as e:
            return False
