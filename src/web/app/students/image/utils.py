# -*- encoding: utf-8 -*-
# Copyrigt 2016 Vinzor Co.,Ltd.
#
# Image instance utils
#
# 2016/4/7 qinjinghui : Init

import time
import logging
import datetime
import json
import functools
from threading import Thread
from ... import db
from ... import app
from flask import current_app
from ...models import Desktop, DesktopType, DesktopState,\
    DesktopTask, TaskAction, TaskResult, TaskState, Image, User
from ... import celery_tasks

from phoenix.cloud import compute as OpenstackComputeService
from phoenix.cloud import image as OpenstackImageService

LOG = logging.getLogger(__name__)


def create_instance(name, image_id, flavor_id,network_ref, user_id):
    try:
        desktop = Desktop()
        desktop.name = name
        desktop.vm_ref = None
        desktop.desktop_type = DesktopType.TEMPLATE
        desktop.start_datetime = datetime.datetime.now()
        desktop.end_datetime = datetime.datetime(3016, 1, 1, 0, 0, 0, 1)
        desktop.desktop_state = DesktopState.SPAWNING
        desktop.image_ref = image_id
        desktop.flavor_ref = flavor_id
        desktop.owner_id = user_id
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
            'desktop_name': name,
            'owner': user_id,
            'desktop': desktop.id,
            'vm_name': ('T-' + name)[:64],
            'start_datetime':  datetime.datetime.now().isoformat(),
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
            'desktop_type': DesktopType.TEMPLATE,
        })
        db.session.add(create_instance_task)
        db.session.commit()
        db.session.flush()

        celery_tasks.run_desktoptask(task_id=create_instance_task.id,
                                     link=celery_tasks._create_desktop_detect.s(
                                         task_id=create_instance_task.id),
                                     link_error=celery_tasks._create_desktop_detect.s(
                                         task_id=create_instance_task.id))

        return True, name
    except:
        LOG.exception('Create failed for vm instance:: %s %s' % (image_id,flavor_id))
        return False, ""


def with_app_context(func):
    """ Wrap a task with flask app context
    """
    @functools.wraps(func)
    def inner_func(*args, **kwargs):
        from .. import app
        from flask import current_app
        try:
            current_app._get_current_object()
        except:
            with app.app_context():
                return func(*args, **kwargs)
        return func(*args, **kwargs)
    return inner_func


def delete_instance(vmid):
    try:
        # Add Delete Instance Task
        desktop = Desktop.query.filter_by(vm_ref=vmid).first()
        if desktop.vm_state == DesktopState.DELETING:
            return "success"
        delete_instance_task = DesktopTask()
        delete_instance_task.action = TaskAction.DELETE
        delete_instance_task.state = 'PENDING'
        delete_instance_task.stage_chain = json.dumps(['DELETE'])
        delete_instance_task.stage = 'DELETE'
        delete_instance_task.context = json.dumps({
            'vm': vmid,
            'desktop': desktop.id
        })
        desktop.desktop_state = 'DELETING'
        db.session.add(desktop)
        db.session.add(delete_instance_task)
        db.session.commit()
        celery_tasks.run_desktoptask(task_id=delete_instance_task.id)
        return "success"
    except:
        LOG.exception('Delete vm instance failed %s' % vmid)
        return "error"


@with_app_context
def create_snapshot(vmid, name, user_id, description):
    try:
        desktop = Desktop.query.filter_by(vm_ref=vmid).first()
        if not desktop:
            return False
        desktop.desktop_state = DesktopState.STOPPING
        db.session.add(desktop)
        db.session.commit()

        #Add Snapshot Instance task
        snapshot_instance_task = DesktopTask()
        snapshot_instance_task.state = 'PENDING'
        snapshot_instance_task.action = TaskAction.SNAPSHOT
        snapshot_instance_task.stage_chain = json.dumps(
            ['STOP', 'WAIT','SNAPSHOT','WAIT_IMAGE'])
        snapshot_instance_task.stage = 'STOP'
        snapshot_instance_task.context = json.dumps({
            'course_name': None,
            'serial': None,
            'desktop': desktop.id,
            'image_name': name,
            'user_id': user_id,
            'description': description,
            'wait_state': 'SHUTOFF',
            'wait_timeout': 10 * 60,
            'desktop_state_map': {'SUCCESS': 'SHUTOFF', 'ERROR': 'ERROR'}
        })
        db.session.add(snapshot_instance_task)
        db.session.commit()

        celery_tasks.run_desktoptask(task_id=snapshot_instance_task.id)

        #create_snapshot
        image_id = OpenstackComputeService.create_image_from_server(server=vmid, image_name=name)

        image_extra_specs = Image()
        image_extra_specs.name = name
        image_extra_specs.ref_id = image_id
        image_extra_specs.owner_id = user_id
        image_extra_specs.description = description
        user = User.query.filter_by(id=user_id).first()
        if user.is_administrator():
            image_extra_specs.visibility = 'public'
        else:
            image_extra_specs.visibility = 'private'
        db.session.add(image_extra_specs)
        db.session.commit()


        return True
    except:
        LOG.exception('Create snapshot failed for vm %s' % vmid)
        return False


@with_app_context
def power_on(vmid):
    try:
        desktop = Desktop.query.filter_by(vm_ref=vmid).first()
        desktop.desktop_state = DesktopState.STARTING
        db.session.add(desktop)
        db.session.commit()

        # Add PowerOn Instance Task
        poweron_instance_task = DesktopTask()
        poweron_instance_task.state = 'PENDING'
        poweron_instance_task.action = TaskAction.START
        poweron_instance_task.stage_chain = json.dumps(
            ['START', 'WAIT'])
        poweron_instance_task.stage = 'START'
        poweron_instance_task.context = json.dumps({
            'course_name': None,
            'serial': None,
            'desktop': desktop.id,
            'wait_state': 'ACTIVE',
            'wait_timeout': 10 * 60,
            'desktop_state_map': {'SUCCESS': 'ACTIVE', 'ERROR': 'ERROR'}
        })
        db.session.add(poweron_instance_task)
        db.session.commit()

        celery_tasks.run_desktoptask(task_id=poweron_instance_task.id)
        return True, desktop.name
    except:
        LOG.exception("Power On image instance failed for %s" % vmid)
        return False, ""


@with_app_context
def power_off(vmid):
    try:
        desktop = Desktop.query.filter_by(vm_ref=vmid).first()
        desktop.desktop_state = DesktopState.STOPPING
        db.session.add(desktop)
        db.session.commit()

        # Add Poweroff Instance Task
        poweroff_instance_task = DesktopTask()
        poweroff_instance_task.state = 'PENDING'
        poweroff_instance_task.action = TaskAction.STOP
        poweroff_instance_task.stage_chain = json.dumps(
            ['STOP', 'WAIT'])
        poweroff_instance_task.stage = 'STOP'
        poweroff_instance_task.context = json.dumps({
            'course_name': None,
            'serial': None,
            'desktop': desktop.id,
            'wait_state': 'SHUTOFF',
            'wait_timeout': 10 * 60,
            'desktop_state_map':{'SUCCESS':'SHUTOFF','ERROR':'ERROR'}
        })
        db.session.add(poweroff_instance_task)
        db.session.commit()

        celery_tasks.run_desktoptask(task_id=poweroff_instance_task.id)
        return True, desktop.name
    except:
        LOG.exception('Power Off image instance failed for: %s ' % vmid)
        return False, ""


def get_instance_console(vmid):
    console_type_list = ['vnc', 'spice', 'rdp']
    console_sub_type_list = {'vnc': 'novnc',
                             'spice': 'spice-html5',
                             'rdp': 'rdp-html5'}
    instance = None
    for console_type in console_type_list:
        try:
            instance = OpenstackComputeService.get_server_console(
                server=vmid, console_type=console_type,
                console_sub_type=console_sub_type_list[console_type])
            if instance:
                break
        except:
            instance = None
            continue
    if instance:
        return instance['console']['url']
    else:
        return None

