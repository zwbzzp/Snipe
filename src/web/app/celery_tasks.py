# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# Celery tasks
#
# 2016/2/22 fengyc : Init

import datetime
import iso8601
import json
import logging
from string import Template
from flask import current_app
from celery import current_app as current_celery
from celery import chain

from . import db
from .models import Course, Lesson, Desktop, Period, DesktopTask, StageResult
from .models import DesktopType, TaskAction, TaskState, User, DesktopState, TaskResult
from .models import User, Parameter, Image
from phoenix.cloud import compute, network, image
from phoenix.cloud.admin import compute as AdminCompute
from phoenix.common import lock
from .audit import ResourceController

LOG = logging.getLogger('celery')

celery = current_celery


@celery.task
def send_mail(msg):
    from . import mail
    mail.send(msg)


@celery.task(name='sync_openstack')
def sync_openstack():
    """ Synchronise openstack resources
    """
    # floating ip
    from phoenix.cloud.openstack.sync_openstack import floating_ip_manager
    floating_ip_manager.refresh()


def assign_desktop_name(course=None, image='win7', serial=0, **kwargs):
    """ Assign a desktop name
    :param course: course name or None
    :param image: image name or None
    :param serial: serial number of desktop
    :param kwargs: other arguments
    :return: name of desktop
    """
    if course:
        template = Template('${course}-${image}_${serial}')
    else:
        template = Template('${image}_${serial}')
    if kwargs is None:
        kwargs = {}
    kwargs = kwargs.copy()
    kwargs['course'] = course
    kwargs['image'] = image
    kwargs['serial'] = serial
    desktop_name = template.substitute(**kwargs)[:64]
    return desktop_name


def assign_course_vm_name(**kwargs):
    """ Assign a vm name
    :param kwargs:
    :return:
    """
    template = Template('C-${course}_${serial}')
    vm_name = template.substitute(**kwargs)[:64]
    return vm_name


def assign_static_vm_name(**kwargs):
    template = Template('S-${owner}_${serial}')
    vm_name = template.substitute(**kwargs)[:64]
    return vm_name


#############
# cloud task
#############

@celery.task(name='schedule_start_lesson')
def schedule_start_lesson(ahead=datetime.timedelta(minutes=10)):
    LOG.info('Scheduling start lesson tasks')
    try:
        course_schedule_ahead = Parameter.query.filter_by(name='course_schedule_ahead').first()
        if not course_schedule_ahead:
            course_schedule_ahead_time = 0
        else:
            course_schedule_ahead_time = course_schedule_ahead.value
    except:
        course_schedule_ahead_time = 0
    ahead = datetime.timedelta(minutes=int(course_schedule_ahead_time))
    now = datetime.datetime.now()
    start_datetime = now + ahead
    start_date = start_datetime.date()
    start_time = start_datetime.time()
    lock_file = 'schedule_start_lesson'
    LOG.debug('Try to lock %s' % lock_file)
    try:
        with lock.FileLock(lock_file) as flock:
            db.session.expunge_all()
            query = Lesson.query.filter_by(scheduled=False)
            query = query.filter(db.and_(
                db.or_(Lesson.start_date < start_date,
                       db.and_(Lesson.start_date == start_date,
                               Lesson._start_time < start_time)),
                db.or_(Lesson.end_date > now.date(),
                       db.and_(Lesson.end_date == now.date(),
                               Lesson._end_time > now.time()))))
            query = query.filter(Lesson.course_id != None)

            lessons = query.all()
            LOG.debug('There are %s lessons need to be scheduled' % len(lessons))

            tasks = []
            for lesson in lessons:
                course = lesson.course
                if course.start_date > start_date or course.end_date < start_date:
                    LOG.warning('Course %r (%s to %s) is expired' % (
                        course, course.start_date, course.end_date))
                    continue
                LOG.info('Scheduling %r' % course)

                # Update current desktops end_datetime
                update_query = Desktop.query.filter(Desktop.course_id == course.id).filter(
                    Desktop.end_datetime <= lesson.end_datetime
                )
                count = update_query.update({Desktop.end_datetime: lesson.end_datetime})
                LOG.info('Update end datetime of %s desktops in course %s to %s' % (count, course, lesson.end_datetime))

                desktop_count = course.desktops.count()
                max_desktop_count = ResourceController().lesson_max_desktop_count(lesson)
                while desktop_count < max_desktop_count:
                    current_serial = desktop_count
                    task = DesktopTask()
                    task.state = 'PENDING'
                    task.stage_chain = json.dumps(['BUILD', 'WAIT', 'FLOATING', 'DETECT'])
                    task.stage = 'BUILD'
                    task.context = json.dumps({
                        'course': course.id,
                        'course_name': course.name,
                        'serial': current_serial,
                        'start_datetime': lesson.start_datetime.isoformat(),
                        'end_datetime': lesson.end_datetime.isoformat(),
                        'flavor': course.flavor_ref,
                        'image': course.image_ref,
                        'network': course.network_ref,
                        'desktop_type': DesktopType.COURSE,
                        'subnet': None,
                        'port': None,
                        'disk': None,
                        'wait_state': 'ACTIVE',
                        'wait_timeout': 10*60,
                        'floating_action': 'ASSIGN',
                        'detect_method': 'PING',
                        'detect_timeout': 30,
                        'desktop_state_map': {
                            TaskResult.SUCCESS: DesktopState.ACTIVE,
                            TaskResult.ERROR: DesktopState.ERROR
                        }
                    })
                    db.session.add(task)
                    desktop_count += 1
                    tasks.append(task)
                lesson.scheduled = True
                lesson.scheduled_at = datetime.datetime.now()
                db.session.add(lesson)
                db.session.commit()
            db.session.commit()
            db.session.flush()
            for task in tasks:
                run_desktoptask(task_id=task.id)
    except lock.FileLockException as ex:
        LOG.warning('Failed to lock %s' % lock_file)


@celery.task(name='schedule_clean_desktops')
def schedule_clean_desktops(latency=60):
    LOG.debug('Scheduling clean expired desktops')
    now = datetime.datetime.now()
    try:
        course_schedule_latency = Parameter.query.filter_by(name='course_schedule_latency').first()
        if not course_schedule_latency:
            course_schedule_latency_time = 0
        else:
            course_schedule_latency_time = course_schedule_latency.value
    except:
        course_schedule_latency_time = 0

    end_at = now - datetime.timedelta(minutes=int(course_schedule_latency_time))
    lock_file = 'schedule_clean_desktops'
    LOG.debug('Try to lock %s' % lock_file)
    try:
        with lock.FileLock(lock_file) as flock:
            query = Desktop.query.filter(Desktop.end_datetime < end_at)
            query = query.filter(Desktop.desktop_state != 'DELETING')
            query = query.filter(Desktop.desktop_state != 'DELETED')
            desktops = query.all()
            LOG.debug('There are %s desktops need to be cleaned' % len(desktops))

            tasks = []
            for desktop in desktops:
                # create a task
                task = DesktopTask()
                task.action = TaskAction.DELETE
                task.state = 'PENDING'
                task.stage_chain = json.dumps(['DELETE'])
                task.stage = 'DELETE'
                task.context = json.dumps({
                    'vm': desktop.vm_ref,
                    'desktop': desktop.id,
                    'course': desktop.course_id
                })
                desktop.desktop_state = 'DELETING'
                db.session.add(desktop)
                db.session.add(task)
                tasks.append(task)
            db.session.commit()
            for task in tasks:
                run_desktoptask(task_id=task.id)
    except lock.FileLockException as ex:
        LOG.warning('Failed to lock %s' % lock_file)


# @celery.task(name='schedule_task_build_desktop')
# def schedule_task_build_desktop():
#     LOG.info('Scheduling build desktop tasks')
#     lock_file = 'schedule_task_build_desktop'
#     LOG.debug('Try to lock %s' % lock_file)
#     try:
#         with lock.FileLock(lock_file) as flock:
#             query = DesktopTask.query.filter(DesktopTask.state.in_(['PENDING', 'RUNNING']))
#             query = query.filter(DesktopTask.stage == 'BUILD')
#             tasks = query.all()
#             LOG.debug('There are %s build desktop tasks' % len(tasks))
#
#             for task in tasks:
#                 try:
#                     context = json.loads(task.context)
#                     LOG.info('Build desktop for %r' % task)
#                     LOG.debug('Task context: %r' % context)
#
#                     # desktop name and vm name
#                     desktop_name = context.get('desktop_name')
#                     vm_name = context.get('vm_name')
#                     vm_name = vm_name if vm_name else desktop_name
#                     if not desktop_name or not vm_name:
#                         image_name = image.get_image(context['image']).name
#                         serial = 0
#                         course_name = None
#                         if context.get('course') is not None:
#                             course = Course.query.filter_by(id=context['course']).first()
#                             if course is not None:
#                                 course_name = course.name
#                         if context.get('serial') is not None:
#                             serial = context['serial']
#                         if not desktop_name:
#                             desktop_name = assign_desktop_name(course_name, image_name, serial)
#                         if not vm_name:
#                             vm_name = assign_course_vm_name(course=course_name, serial=serial)
#
#                     task.state = TaskState.RUNNING
#                     db.session.add(task)
#                     db.session.commit()
#
#                     # create a vm
#                     reqargs = {
#                         'name': vm_name,
#                         'image': context['image'],
#                         'flavor': context['flavor'],
#                     }
#                     if context.get('port') is not None:
#                         reqargs['network'] = {'port-id': context['port']}
#                     elif context.get('network') is not None:
#                         # reqargs['network'] = {'net-id': context['network']}
#                         reqargs['nics'] = [{'net-id': context['network']}]
#                     instance = compute.create_server(**reqargs)
#                 except:
#                     LOG.exception('Unable to build a desktop for %r' % task)
#                     task.record_stage(False)
#                     task.retries += 1
#                     db.session.add(task)
#                     db.session.commit()
#                     if task.retries >= 3:
#                         LOG.error('Failed to build a desktop, too many retries')
#                         task.go_error()
#                     continue
#
#                 # record in desktop
#                 start_datetime = iso8601.parse_date(context['start_datetime'], None)
#                 end_datetime = iso8601.parse_date(context['end_datetime'], None)
#
#                 desktop_type = context.get('desktop_type', None)
#                 desktop = Desktop(name=desktop_name, course_id=context.get('course'),
#                                   vm_ref=instance.id, desktop_type=desktop_type, start_datetime=start_datetime,
#                                   end_datetime=end_datetime)
#                 if context.get('owner') is not None:
#                     owner = User.query.filter_by(id=context['owner']).first()
#                     desktop.owner = owner
#                 db.session.add(desktop)
#                 db.session.commit()
#
#                 # update task context and go to next stage
#                 context['vm'] = instance.id
#                 context['desktop'] = desktop.id
#                 task.context = json.dumps(context)
#                 task.record_stage()
#                 task.go_next()
#
#                 LOG.info('Build desktop for %r, success' % task)
#                 LOG.debug('Task context: %r' % context)
#     except lock.FileLockException as ex:
#         LOG.warning('Failed to lock %s' % lock_file)
#
#
# @celery.task(name='schedule_task_wait_state')
# def schedule_task_wait_state():
#     LOG.info('Scheduling wait desktop state tasks')
#     lock_file = 'schedule_task_wait_state'
#     LOG.debug('Try to lock %s' % lock_file)
#     try:
#         with lock.FileLock(lock_file) as flock:
#             query = DesktopTask.query.filter(DesktopTask.stage == 'WAIT')
#             query = query.filter(DesktopTask.state != 'FINISHED')
#             tasks = query.all()
#             LOG.debug('There are %s wait desktop state tasks' % len(tasks))
#
#             ERROR_STATES = ['ERROR']
#
#             for task in tasks:
#                 context = json.loads(task.context)
#                 LOG.info('Wait state for %r' % task)
#                 LOG.debug('Task context: %r' % context)
#
#                 # The first time to check vm state
#                 if context.get('wait_started_at') is None:
#                     context['wait_started_at'] = datetime.datetime.now().isoformat()
#                     task.context = json.dumps(context)
#                 if context.get('wait_timeout') is None:
#                     context['wait_timeout'] = 10*60
#                     task.context = json.dumps(context)
#                 db.session.add(task)
#                 db.session.commit()
#
#                 # Get state of vm
#                 try:
#                     instance = compute.get_server(context['vm'])
#                 except:
#                     # unable to connect to openstack ?
#                     LOG.exception('Unable to get desktop state for %r' % task)
#                     task.record_stage(False)
#                     task.retries += 1
#                     if task.retries >= 3:
#                         LOG.error('Failed to get desktop state for %r, too many retires' % task)
#                         task.go_error()
#                     db.session.add(task)
#                     db.session.commit()
#                     continue
#                 LOG.debug('Wait state for %r, desktop state is %r' % (task, instance.status))
#
#                 # Update desktop
#                 if context.get('desktop') is not None:
#                     desktop = Desktop.query.filter_by(id=context['desktop']).first()
#                     if desktop is not None:
#                         desktop.vm_state = instance.status
#                         db.session.add(desktop)
#                         db.session.commit()
#
#                 # Check state
#                 if instance.status in ERROR_STATES:
#                     LOG.error('Wait state for %r, but desktop state is ERROR' % task)
#                     task.record_stage(False, 'Wait state for %r, but desktop state is ERROR' % task)
#                     task.go_error()
#                 elif instance.status == context['wait_state']:
#                     LOG.info('Wait state for %r, stage success' % task)
#                     task.record_stage()
#                     task.go_next()
#                 else:
#                     # Time out ?
#                     started_at = iso8601.parse_date(context['wait_started_at'], None)
#                     wait_delta = datetime.datetime.now() - started_at
#                     if wait_delta.seconds > context['wait_timeout']:
#                         LOG.error('Wait state for %r, but time out' % task)
#                         task.record_stage(False, 'Wait state for %r, but time out' % task)
#                         task.go_error()
#     except lock.FileLockException as ex:
#         LOG.warning('Failed to lock %s' % lock_file)
#
#
# @celery.task(name='schedule_task_floating')
# def schedule_task_floating():
#     LOG.info('Scheduling floating tasks')
#     lock_file = 'schedule_task_floating'
#     LOG.debug('Try to lock %s' % lock_file)
#     try:
#         with lock.FileLock(lock_file) as flock:
#             query = DesktopTask.query.filter(DesktopTask.stage == 'FLOATING')
#             query = query.filter(DesktopTask.state != 'FINISHED')
#             tasks = query.all()
#             LOG.debug('There are %s floating tasks' % len(tasks))
#
#             for task in tasks:
#                 context = json.loads(task.context)
#                 LOG.info('Floating for %r' % task)
#                 LOG.debug('Task context: %r' % context)
#                 instance_id = context['vm']
#
#                 try:
#                     floating_ip = network.associate_floating_ip(instance_id)
#                 except:
#                     LOG.exception('Unable to associate a floating ip for %r' % task)
#                     task.record_stage(False)
#                     task.retries += 1
#                     db.session.add(task)
#                     db.session.commit()
#                     if task.retries >= 3:
#                         LOG.error('Failed to associate a floating ip, too many retries')
#                         task.go_error()
#                     continue
#                 LOG.debug('')
#                 context['floating_ip'] = floating_ip
#                 task.context = json.dumps(context)
#
#                 # update desktop
#                 if context.get('desktop') is not None:
#                     desktop = Desktop.query.filter_by(id=context['desktop']).first()
#                     if desktop is not None:
#                         desktop.floating_ip = floating_ip
#                         desktop.need_floating = False
#                         db.session.add(desktop)
#                         db.session.commit()
#
#                 # record stage result
#                 task.record_stage()
#
#                 # next stage
#                 task.go_next()
#
#                 LOG.info('Associate floating ip success, instance id: %s' % instance_id)
#                 LOG.debug('Task context: %r' % context)
#     except lock.FileLockException as ex:
#         LOG.warning('Failed to lock %s' % lock_file)
#
#
# def send_udp_detect_message(ip, port, message='vinzor', timeout=1):
#     """ Send udp message
#     """
#     LOG.debug('Send udp message to %r' % ((ip, port),))
#     from socket import socket, AF_INET, SOCK_DGRAM
#     s = socket(AF_INET, SOCK_DGRAM)
#     s.settimeout(timeout)
#     s.sendto(message.encode(encoding='utf8'), (ip, port))
#     s.close()
#
#
# @celery.task(name='schedule_task_detect_desktop')
# def schedule_task_detect_desktop():
#     LOG.info('Scheduling detect tasks')
#     lock_file = 'schedule_task_detect_desktop'
#     LOG.debug('Try to lock %s' % lock_file)
#     try:
#         with lock.FileLock(lock_file):
#             query = DesktopTask.query.filter(DesktopTask.stage == 'DETECT')
#             query = query.filter(DesktopTask.state != 'FINISHED')
#             tasks = query.all()
#             LOG.debug('There are %s detect tasks' % len(tasks))
#
#             mapping = {}
#             current_app_obj = current_app._get_current_object()
#
#             # # FIXME start a udp listener, this should be duplicated !!
#             # from socketserver import ThreadingUDPServer, DatagramRequestHandler
#             # import threading
#             #
#             # class DetectUDPHandler(DatagramRequestHandler):
#             #     def handle(self):
#             #         client_address = self.client_address
#             #         data = self.rfile.read(1024)
#             #         message = data.decode(encoding='utf8').strip()
#             #         LOG.debug('Received udp message from %r' % client_address)
#             #         if message == 'vinzor':
#             #             LOG.info('Detect receive message from %r' % client_address)
#             #             task = mapping.get(client_address[0])
#             #             if task is not None:
#             #                 with current_app_obj.app_context():
#             #                     self.update_task(task)
#             #
#             #     def update_task(self, task_id):
#             #         task = DesktopTask.query.filter_by(id=task_id).first()
#             #         context = json.loads(task.context)
#             #         if task is not None and task.stage == 'DETECT':
#             #             desktop = Desktop.query.filter_by(id=context['desktop']).first()
#             #             desktop.go_active()
#             #             task.go_next()
#
#             # udp_listener = None
#             # udp_thread = None
#             #
#             # if len(tasks):
#             #     # FIXME udp port
#             #     try:
#             #         udp_listener = ThreadingUDPServer(('0.0.0.0', 10000), DetectUDPHandler)
#             #         udp_thread = threading.Thread(target=udp_listener.serve_forever)
#             #         udp_thread.start()
#             #     except Exception as ex:
#             #         LOG.exception(ex)
#
#             for task in tasks:
#                 context = json.loads(task.context)
#                 LOG.info('Detect for %r' % task)
#                 LOG.debug('Task context: %r' % context)
#
#                 # first time?
#                 if context.get('detect_started_at') is None:
#                     context['detect_started_at'] = datetime.datetime.now().isoformat()
#                     task.context = json.dumps(context)
#                 if context.get('detect_timeout') is None:
#                     context['detect_timeout'] = 10
#                     task.context = json.dumps(context)
#                 db.session.add(task)
#                 db.session.commit()
#
#                 detect_method = context['detect_method']
#                 floating_ip = context.get('floating_ip')
#                 if floating_ip is None:
#                     LOG.error('Detect for %r, no floating ip' % task)
#                     task.go_error()
#                     continue
#                 mapping[floating_ip] = task
#
#                 # detect
#                 if detect_method == 'PING':
#                     from phoenix.common.ping import ping
#                     try:
#                         if ping(floating_ip):
#                             LOG.info('Detect for %r, success' % task)
#                             desktop = Desktop.query.filter_by(id=context['desktop']).first()
#                             desktop.go_active()
#                             task.record_stage()
#                             task.go_next()
#                             continue
#                     except:
#                         LOG.exception('Detect(ping) for %r, fail' % task)
#
#                 elif detect_method == 'UDP':
#                     pass
#                     # udp_port = context.get('detect_udp_port') or 43279
#                     # udp_message = context.get('detect_udp_message') or 'vinzor'
#                     # try:
#                     #     send_udp_detect_message(floating_ip, udp_port, udp_message)
#                     # except:
#                     #     # Doesn't care what happened
#                     #     LOG.exception('Detect for %r, network exception' % task)
#                 else:
#                     LOG.error('Detect for %r, unknown detect method' % task)
#                     task.record_stage(False, 'Unknown detect method')
#                     task.go_error()
#                     continue
#
#             # # now wait shutdown the udp listener
#             # if udp_listener is not None:
#             #     import time
#             #     time.sleep(1)
#             #     udp_listener.shutdown()
#             #     udp_listener.server_close()
#             #     udp_thread.join(1)
#
#             # and timeout?
#             for task in tasks:
#                 if task.stage == 'DETECT' and task.state != 'FINISHED':
#                     started_at = iso8601.parse_date(context['detect_started_at'], None)
#                     delta = datetime.datetime.now() - started_at
#                     if delta.seconds > context['detect_timeout']:
#                         LOG.error('Detect for %r, timeout' % task)
#                         task.record_stage(False, 'Detect time out')
#                         task.go_error()
#     except lock.FileLockException as ex:
#         LOG.warning('Failed to lock %s' % lock_file)
#
#
# @celery.task(name='schedule_task_delete_desktop')
# def schedule_task_delete_desktop():
#     LOG.info('Scheduling delete desktop tasks')
#     lock_file = 'schedule_task_delete_desktop'
#     LOG.debug('Try to lock %s' % lock_file)
#     try:
#         with lock.FileLock(lock_file) as flock:
#             query = DesktopTask.query.filter(DesktopTask.stage == 'DELETE')
#             query = query.filter(DesktopTask.state != 'FINISHED')
#             tasks = query.all()
#
#             for task in tasks:
#                 context = json.loads(task.context)
#                 LOG.info('Delete desktop for %r' % task)
#                 LOG.debug('Task context: %r' % context)
#
#                 from novaclient.exceptions import NotFound
#
#                 try:
#                     # TODO need to release floating ip
#                     compute.delete_server(context['vm'])
#                     network.disassociate_floating_ip(context['vm'])
#                 except NotFound as ex:
#                     LOG.warning('VM %s of desktop %s not found' % (context['vm'], context['desktop']))
#                 except:
#                     LOG.exception('Unable to delete desktop for %r' % task)
#                     task.retries += 1
#                     if task.retries >= 3:
#                         LOG.error('Failed to delete desktop for %r, too many retries')
#                         task.go_error()
#                     db.session.add(task)
#                     db.session.commit()
#                     continue
#
#                 LOG.info('Delete desktop for %r, success' % task)
#                 if context.get('desktop') is not None:
#                     # FIXME delete a desktop or soft delete?
#                     Desktop.query.filter_by(id=context['desktop']).delete()
#                 task.go_next()
#     except lock.FileLockException as ex:
#         LOG.warning('Failed to lock %s' % lock_file)



def run_desktoptask(task_id, link=None, link_error=None):
    db.session.flush()  # do a flush before start the task
    task = DesktopTask.query.filter_by(id=task_id).first()
    if not task:
        LOG.warning('Could not build desktop for task %s, task not exists' % task_id)
        return
    sub_tasks = []
    for stage in json.loads(task.stage_chain):
        if stage == 'BUILD':
            sub_tasks.append(build_desktop.subtask((), {'task_id':task_id}))
        elif stage == 'WAIT':
            sub_tasks.append(wait_desktop.subtask((), {'task_id':task_id}, countdown=3))
        elif stage == 'FLOATING':
            sub_tasks.append(assign_floating.subtask((), {'task_id':task_id}, countdown=1))
        elif stage == 'DETECT':
            sub_tasks.append(detect_floating.subtask((), {'task_id':task_id}, countdown=3))
        elif stage == 'DELETE':
            sub_tasks.append(delete_desktop.s(task_id=task_id))
        elif stage == 'REBOOT':
            sub_tasks.append(reboot_desktop.s(task_id=task_id))
        elif stage == 'REBUILD':
            sub_tasks.append(rebuild_desktop.s(task_id=task_id))
        elif stage == 'START':
            sub_tasks.append(start_desktop.s(task_id=task_id))
        elif stage == 'STOP':
            sub_tasks.append(stop_desktop.s(task_id=task_id))
        elif stage == 'SUSPEND':
            sub_tasks.append(suspend_desktop.s(task_id=task_id))
        elif stage == 'RESUME':
            sub_tasks.append(resume_desktop.s(task_id=task_id))
        elif stage == 'SNAPSHOT':
            sub_tasks.append(snapshot_desktop.s(task_id=task_id))
        elif stage == 'WAIT_IMAGE':
            sub_tasks.append(wait_image.s(task_id=task_id))


    c = chain(*sub_tasks)
    if link:
        c.link(set_desktop_state.s(task_id=task_id) | link)
    else:
        c.link(set_desktop_state.s(task_id=task_id))
    if link_error:
        c.link_error(set_desktop_state.s(task_id=task_id) | link_error)
    else:
        c.link_error(set_desktop_state.s(task_id=task_id))
    c.apply_async(countdown=1)


@celery.task(name='build_desktop', bind=True, max_retries=3, default_retry_delay=10)
def build_desktop(self, *args, **kwargs):
    db.session.expunge_all()
    task_id = kwargs['task_id']
    task = DesktopTask.query.filter_by(id=task_id).first()
    if not task:
        LOG.warning('Could not build desktop for task %s, task not exists' % task_id)
        return
    if task.stage == TaskState.FINISHED or task.stage != 'BUILD':
        LOG.warning('Skip build for %r, task finished or not in build stage' % task)
        return
    LOG.info('Build desktop for %r' % task)
    LOG.debug('Task context: %r' % task.context)

    # build a desktop
    try:
        # create a desktop
        course = Course.query.filter_by(id=task.get('course')).first()
        course_name = course.name if course else ''
        image_name = image.get_image(task['image']).name
        serial = task.get('serial') or 0
        if task.get('desktop') is None:
            desktop_name = task.get('desktop_name')
            if not desktop_name:
                desktop_name = assign_desktop_name(course_name, image_name, serial)
            start_datetime = datetime.datetime.now()
            if task.get('end_datetime'):
                end_datetime = iso8601.parse_date(task['end_datetime'], None)
            else:
                end_datetime = None
            desktop_type = task.get('desktop_type')
            if not desktop_type:
                desktop_type = DesktopType.COURSE if course.get('course') else DesktopType.STATIC
            desktop = Desktop(name=desktop_name, course_id=task.get('course'),
                              vm_ref=None, desktop_type=desktop_type, start_datetime=start_datetime,
                              end_datetime=end_datetime, image_ref=task['image'],
                              flavor_ref=task['flavor'])
            desktop.desktop_state = DesktopState.BUILD
            if task.get('owner') is not None:
                owner = User.query.filter_by(id=task['owner']).first()
                desktop.owner = owner
            db.session.add(desktop)
            db.session.commit()
            task['desktop'] = desktop.id
            #task.state = TaskState.RUNNING
            db.session.add(task)
            db.session.commit()
        desktop = Desktop.query.filter_by(id=task['desktop']).first()
        task.state = TaskState.RUNNING
        db.session.add(task)
        db.session.commit()

        # create a vm
        vm_name = task.get('vm_name')
        if vm_name is None:
            if desktop.desktop_type == DesktopType.COURSE:
                vm_name = assign_course_vm_name(course=course_name, serial=serial)
            else:
                owner = User.query.filter_by(id=task['owner']).first()
                vm_name = assign_static_vm_name(owner=owner.username, serial=serial)
        req = {
            'name': vm_name,
            'image': task['image'],
            'flavor': task['flavor'],
        }
        if task.get('port') is not None:
            req['network'] = {'port-id': task['port']}
        elif task.get('network') is not None:
            req['nics'] = [{'net-id': task['network']}]

        instance = compute.create_server(**req)
        desktop.vm_ref = instance.id
        db.session.add(desktop)
        task['vm'] = instance.id
        task.record_stage()
        task.go_next()
        db.session.commit()
        db.session.flush()
        LOG.info('Build desktop for %r, success' % task)
        LOG.debug('Task context: %r' % task.context)
    except Exception as ex:
        LOG.exception('Unable to build a desktop for %r' % task)
        task.record_stage(False)
        task.retries += 1
        db.session.add(task)
        db.session.commit()
        if task.retries >= 3:
            LOG.error('Failed to build a desktop, too many retries')
            task.go_error()
            desktop.desktop_state = DesktopState.ERROR
            db.session.add(desktop)
            db.session.commit()
        else:
            raise self.retry(exc=ex)


@celery.task(name='rebuild_desktop', bind=True, max_retries=3, default_retry_delay=10)
def rebuild_desktop(self, *args, **kwargs):
    db.session.expunge_all()
    task_id = kwargs['task_id']
    task = DesktopTask.query.filter_by(id=task_id).first()
    if not task:
        LOG.warning('Could not rebuild desktop for task %s, task not exists' % task_id)
        return
    db.session.refresh(task)
    if task.stage == TaskState.FINISHED or task.stage != 'REBUILD':
        LOG.warning('Skip rebuild for %r, task finished or not in rebuild stage' % task)
        return
    LOG.info('Rebuild desktop for %r' % task)
    LOG.debug('Task context: %r' % task.context)

    # update a desktop which need be rebuild
    desktop = Desktop.query.filter_by(id=task['desktop']).first()
    desktop.desktop_state = DesktopState.REBUILDING
    desktop.image_ref = task['image']
    db.session.add(desktop)
    db.session.commit()
    task.state = TaskState.RUNNING
    db.session.add(task)
    db.session.commit()

    try:
        new_image = image.get_image(task['image'])
        vm = compute.get_server(desktop.vm_ref)

        # rebuild a vm
        req = {
            'server': vm,
            'image': new_image,
        }
        compute.rebuild_server(**req)
        db.session.add(desktop)
        task['vm'] = desktop.vm_ref
        task.record_stage()
        task.go_next()
        db.session.commit()
        LOG.info('Rebuild desktop for %r, success' % task)
        LOG.debug('Task context: %r' % task.context)
    except Exception as ex:
        LOG.exception('Unable to rebuild a desktop for %r' % task)
        task.record_stage(False)
        task.retries += 1
        db.session.add(task)
        db.session.commit()
        if task.retries >= 3:
            LOG.error('Failed to rebuild a desktop, too many retries')
            task.go_error()
            desktop.desktop_state = DesktopState.ERROR
            db.session.add(desktop)
            db.session.commit()
        else:
            raise self.retry(exc=ex)


@celery.task(name='reboot_desktop', bind=True, max_retries=3, default_retry_delay=10)
def reboot_desktop(self, *args, **kwargs):
    task_id = kwargs['task_id']
    task = DesktopTask.query.filter_by(id=task_id).first()
    if not task:
        LOG.warning('Could not reboot desktop for task %s, task not exists' % task_id)
        return
    db.session.refresh(task)
    if task.stage == TaskState.FINISHED or task.stage != 'REBOOT':
        LOG.warning('Skip reboot for %r, task finished or not in reboot stage' % task)
        return
    LOG.info('Reboot desktop for %r' % task)
    LOG.debug('Task context: %r' % task.context)

    # update a desktop which need be rebooted
    desktop = Desktop.query.filter_by(id=task['desktop']).first()
    desktop.desktop_state = DesktopState.REBOOTING
    db.session.add(desktop)
    db.session.commit()
    task.state = TaskState.RUNNING
    db.session.add(task)
    db.session.commit()

    # reboot a vm
    try:
        compute.reboot_server(desktop.vm_ref, soft_reboot=False)
        task['vm'] = desktop.vm_ref
        task.record_stage()
        task.go_next()
        db.session.commit()
        LOG.info('Reboot desktop for %r, success' % task)
        LOG.debug('Task context: %r' % task.context)
    except Exception as ex:
        LOG.exception('Unable to reboot a desktop for %r' % task)
        task.record_stage(False)
        task.retries += 1
        db.session.add(task)
        db.session.commit()
        if task.retries >= 3:
            LOG.error('Failed to reboot a desktop, too many retries')
            task.go_error()
            desktop.desktop_state = DesktopState.ERROR
            db.session.add(desktop)
            db.session.commit()
        else:
            raise self.retry(exc=ex)


@celery.task(name='start_desktop', bind=True, max_retries=3, default_retry_delay=10)
def start_desktop(self, *args, **kwargs):
    task_id = kwargs['task_id']
    task = DesktopTask.query.filter_by(id=task_id).first()
    if not task:
        LOG.warning('Could not start desktop for task %s, task not exists' % task_id)
        return
    db.session.refresh(task)
    if task.stage == TaskState.FINISHED or task.stage != 'START':
        LOG.warning('Skip start for %r, task finished or not in start stage' % task)
        return
    LOG.info('Start desktop for %r' % task)
    LOG.debug('Task context: %r' % task.context)

    # update a desktop which need be rebooted
    desktop = Desktop.query.filter_by(id=task['desktop']).first()
    desktop.desktop_state = DesktopState.STARTING
    db.session.add(desktop)
    db.session.commit()
    task.state = TaskState.RUNNING
    db.session.add(task)
    db.session.commit()

    # start a vm
    try:
        compute.start_server(desktop.vm_ref)
        task['vm'] = desktop.vm_ref
        task.record_stage()
        task.go_next()
        db.session.commit()
        LOG.info('Start desktop for %r, success' % task)
        LOG.debug('Task context: %r' % task.context)
    except Exception as ex:
        LOG.exception('Unable to start a desktop for %r' % task)
        task.record_stage(False)
        task.retries += 1
        db.session.add(task)
        db.session.commit()
        if task.retries >= 3:
            LOG.error('Failed to start a desktop, too many retries')
            task.go_error()
            desktop.desktop_state = DesktopState.ERROR
            db.session.add(desktop)
            db.session.commit()
        else:
            raise self.retry(exc=ex)


@celery.task(name='stop_desktop', bind=True, max_retries=3, default_retry_delay=10)
def stop_desktop(self, *args, **kwargs):
    task_id = kwargs['task_id']
    task = DesktopTask.query.filter_by(id=task_id).first()
    if not task:
        LOG.warning('Could not stop desktop for task %s, task not exists' % task_id)
        return
    db.session.refresh(task)
    if task.stage == TaskState.FINISHED or task.stage != 'STOP':
        LOG.warning('Skip stop for %r, task finished or not in stop stage' % task)
        return
    LOG.info('Stop desktop for %r' % task)
    LOG.debug('Task context: %r' % task.context)

    # update a desktop which need be stopped
    desktop = Desktop.query.filter_by(id=task['desktop']).first()
    desktop.desktop_state = DesktopState.STOPPING
    db.session.add(desktop)
    db.session.commit()
    task.state = TaskState.RUNNING
    db.session.add(task)
    db.session.commit()

    # reboot a vm
    try:
        compute.stop_server(desktop.vm_ref)
        task['vm'] = desktop.vm_ref
        task.record_stage()
        task.go_next()
        db.session.commit()
        LOG.info('Stop desktop for %r, success' % task)
        LOG.debug('Task context: %r' % task.context)
    except Exception as ex:
        LOG.exception('Unable to stop a desktop for %r' % task)
        task.record_stage(False)
        task.retries += 1
        db.session.add(task)
        db.session.commit()
        if task.retries >= 3:
            LOG.error('Failed to stop a desktop, too many retries')
            task.go_error()
            desktop.desktop_state = DesktopState.ERROR
            db.session.add(desktop)
            db.session.commit()
        else:
            raise self.retry(exc=ex)

@celery.task(name='suspend_desktop', bind=True, max_retries=3, default_retry_delay=10)
def suspend_desktop(self, *args, **kwargs):
    task_id = kwargs['task_id']
    task = DesktopTask.query.filter_by(id=task_id).first()
    if not task:
        LOG.warning('Could not suspend desktop for task %s, task not exists' % task_id)
        return
    db.session.refresh(task)
    if task.stage == TaskState.FINISHED or task.stage != 'SUSPEND':
        LOG.warning('Skip suspend for %r, task finished or not in suspend stage' % task)
        return
    LOG.info('Suspend desktop for %r' % task)
    LOG.debug('Task context: %r' % task.context)

    # update a desktop which need be suspended
    desktop = Desktop.query.filter_by(id=task['desktop']).first()
    desktop.desktop_state = DesktopState.SUSPENDING
    db.session.add(desktop)
    db.session.commit()
    task.state = TaskState.RUNNING
    db.session.add(task)
    db.session.commit()

    # suspend a vm
    try:
        compute.suspend_server(desktop.vm_ref)
        task['vm'] = desktop.vm_ref
        task.record_stage()
        task.go_next()
        db.session.commit()
        LOG.info('Suspend desktop for %r, success' % task)
        LOG.debug('Task context: %r' % task.context)
    except Exception as ex:
        LOG.exception('Unable to suspend a desktop for %r' % task)
        task.record_stage(False)
        task.retries += 1
        db.session.add(task)
        db.session.commit()
        if task.retries >= 3:
            LOG.error('Failed to suspend a desktop, too many retries')
            task.go_error()
            desktop.desktop_state = DesktopState.ERROR
            db.session.add(desktop)
            db.session.commit()
        else:
            raise self.retry(exc=ex)


@celery.task(name='resume_desktop', bind=True, max_retries=3, default_retry_delay=10)
def resume_desktop(self, *args, **kwargs):
    task_id = kwargs['task_id']
    task = DesktopTask.query.filter_by(id=task_id).first()
    if not task:
        LOG.warning('Could not resume desktop for task %s, task not exists' % task_id)
        return
    db.session.refresh(task)
    if task.stage == TaskState.FINISHED or task.stage != 'RESUME':
        LOG.warning('Skip resume for %r, task finished or not in resume stage' % task)
        return
    LOG.info('Resume desktop for %r' % task)
    LOG.debug('Task context: %r' % task.context)

    # update a desktop which need be suspended
    desktop = Desktop.query.filter_by(id=task['desktop']).first()
    desktop.desktop_state = DesktopState.STARTING
    db.session.add(desktop)
    db.session.commit()
    task.state = TaskState.RUNNING
    db.session.add(task)
    db.session.commit()

    # resume a vm
    try:
        compute.resume_server(desktop.vm_ref)
        task['vm'] = desktop.vm_ref
        task.record_stage()
        task.go_next()
        db.session.commit()
        LOG.info('Resume desktop for %r, success' % task)
        LOG.debug('Task context: %r' % task.context)
    except Exception as ex:
        LOG.exception('Unable to resume a desktop for %r' % task)
        task.record_stage(False)
        task.retries += 1
        db.session.add(task)
        db.session.commit()
        if task.retries >= 3:
            LOG.error('Failed to resume a desktop, too many retries')
            task.go_error()
            desktop.desktop_state = DesktopState.ERROR
            db.session.add(desktop)
            db.session.commit()
        else:
            raise self.retry(exc=ex)


@celery.task(name='snapshot_desktop', bind=True, max_retries=3, default_retry_delay=10)
def snapshot_desktop(self, *args, **kwargs):
    task_id = kwargs['task_id']
    task = DesktopTask.query.filter_by(id=task_id).first()
    if not task:
        LOG.warning('Could not snapshot desktop for task %s, task not exists' % task_id)
        return
    db.session.refresh(task)
    if task.stage == TaskState.FINISHED or task.stage != 'SNAPSHOT':
        LOG.warning('Skip snapshot for %r, task finished or not in resume stage' % task)
        return
    LOG.info('Snapshot desktop for %r' % task)
    LOG.debug('Task context: %r' % task.context)

    # update a desktop which need be suspended
    desktop = Desktop.query.filter_by(id=task['desktop']).first()
    desktop.desktop_state = DesktopState.SNAPSHOTING
    db.session.add(desktop)
    db.session.commit()
    task.state = TaskState.RUNNING
    db.session.add(task)
    db.session.commit()

    # snapshot a vm
    try:
        image_id = compute.create_image_from_server(server=desktop.vm_ref,image_name=task['image_name'])
        task['image_id'] = image_id
        image_extra_specs = Image()
        image_extra_specs.ref_id = image_id
        image_extra_specs.name = task['image_name']
        image_extra_specs.owner_id = task['user_id']
        user = User.query.filter_by(id=task['user_id']).first()
        if user.is_administrator():
            image_extra_specs.visibility = 'public'
        else:
            image_extra_specs.visibility = 'private'
        image_extra_specs.description = task['description']
        db.session.add(image_extra_specs)
        db.session.commit()

        task.record_stage()
        task.go_next()
        db.session.commit()
        LOG.info('Snapshot desktop for %r, success' % task)
        LOG.debug('Task context: %r' % task.context)
    except Exception as ex:
        LOG.exception('Unable to snapshot a desktop for %r' % task)
        task.record_stage(False)
        task.retries += 1
        db.session.add(task)
        db.session.commit()
        if task.retries >= 3:
            LOG.error('Failed to snapshot a desktop, too many retries')
            task.go_error()
            desktop.desktop_state = DesktopState.ERROR
            db.session.add(desktop)
            db.session.commit()
        else:
            raise self.retry(exc=ex)


@celery.task(name='wait_desktop', bind=True, max_retries=None, default_retry_delay=10)
def wait_desktop(self, *args, **kwargs):
    db.session.expunge_all()
    task_id = kwargs['task_id']
    task = DesktopTask.query.filter_by(id=task_id).first()
    if not task:
        LOG.warning('Could not wait desktop for task %s, task not exists' % task_id)
        return
    db.session.refresh(task)
    if task.stage == TaskState.FINISHED or task.stage != 'WAIT':
        LOG.warning('Skip wait for %r, task finished or not in wait stage' % task)
        return
    LOG.info('Wait state for %r' % task)
    LOG.debug('Task context: %r' % task.context)

    # The first time to check vm state
    if task.get('wait_started_at') is None:
        task['wait_started_at'] = datetime.datetime.now().isoformat()
    if task.get('wait_timeout') is None:
        task['wait_timeout'] = 10*60
    db.session.add(task)
    db.session.commit()

    # Get state of vm
    try:
        instance = compute.get_server(task['vm'])
    except Exception as ex:
        # unable to connect to openstack ?
        LOG.exception('Unable to get desktop state for %r' % task)
        task.record_stage(False)
        task.retries += 1
        db.session.add(task)
        if task.retries >= 3:
            LOG.error('Failed to get desktop state for %r, too many retires' % task)
            task.go_error()
            db.session.add(task)
            db.session.commit()
            return
        db.session.commit()
        if task.retries < 3:
            raise self.retry(exc=ex)

    LOG.debug('Wait state for %r, desktop state is %r' % (task, instance.status))
    # Update desktop
    if task.get('desktop') is not None:
        desktop = Desktop.query.filter_by(id=task['desktop']).first()
        if desktop is not None:
            desktop.vm_state = instance.status
            db.session.add(desktop)
            db.session.commit()
    # Check state
    ERROR_STATES=['ERROR']
    if instance.status in ERROR_STATES:
        LOG.error('Wait state for %r, but desktop state is ERROR' % task)
        task.record_stage(False, 'Wait state for %r, but desktop state is ERROR' % task)
        task.go_error()
    elif instance.status == task['wait_state']:
        LOG.info('Wait state for %r, stage success' % task)
        task.record_stage()
        task.go_next()
    else:
        # Time out ?
        started_at = iso8601.parse_date(task['wait_started_at'], None)
        wait_delta = datetime.datetime.now() - started_at
        if wait_delta.seconds > task['wait_timeout']:
            LOG.error('Wait state for %r, but time out' % task)
            task.record_stage(False, 'Wait state for %r, but time out' % task)
            task.go_error()
        else:
            LOG.debug('Wait state for %r, but state is %s' % (task, instance.status))
            raise self.retry(exc=None)

@celery.task(name='wait_image', bind=True, max_retries=None, default_retry_delay=10)
def wait_image(self, *args, **kwargs):
    task_id = kwargs['task_id']
    task = DesktopTask.query.filter_by(id=task_id).first()
    if not task:
        LOG.warning('Could not wait image for task %s, task not exists' % task_id)
        return
    db.session.refresh(task)
    if task.stage == TaskState.FINISHED or task.stage != 'WAIT_IMAGE':
        LOG.warning('Skip wait for %r, task finished or not in wait stage' % task)
        return
    LOG.info('Wait state for %r' % task)
    LOG.debug('Task context: %r' % task.context)

    # The first time to check vm state
    if task.get('wait_started_at') is None:
        task['wait_started_at'] = datetime.datetime.now().isoformat()
    if task.get('wait_timeout') is None:
        task['wait_timeout'] = 30*60
    db.session.add(task)
    db.session.commit()

    # Get state of image
    try:
        new_image = image.get_image(task['image_id'])
    except Exception as ex:
        # unable to connect to openstack ?
        LOG.exception('Unable to get image state for %r' % task)
        task.record_stage(False)
        task.retries += 1
        db.session.add(task)
        if task.retries >= 3:
            LOG.error('Failed to get image state for %r, too many retires' % task)
            task.go_error()
            db.session.add(task)
            db.session.commit()
            return
        db.session.commit()
        if task.retries < 3:
            raise self.retry(exc=ex)

    LOG.debug('Wait state for %r, image state is %r' % (task, new_image.status))

    # Check state
    ERROR_STATES=['ERROR']
    if new_image.status in ERROR_STATES:
        LOG.error('Wait state for %r, but image state is ERROR' % task)
        task.record_stage(False, 'Wait state for %r, but image state is ERROR' % task)
        task.go_error()
    elif new_image.status == 'active':
        LOG.info('Wait state for %r, stage success' % task)
        task.record_stage()
        task.go_next()
    else:
        # Time out ?
        started_at = iso8601.parse_date(task['wait_started_at'], None)
        wait_delta = datetime.datetime.now() - started_at
        if wait_delta.seconds > task['wait_timeout']:
            LOG.error('Wait state for %r, but time out' % task)
            task.record_stage(False, 'Wait state for %r, but time out' % task)
            task.go_error()
        else:
            LOG.debug('Wait state for %r, but state is %s' % (task, new_image.status))
            raise self.retry(exc=None)


@celery.task(name='assign_floating', bind=True, max_retries=3, default_retry_delay=10)
def assign_floating(self, *args, **kwargs):
    db.session.expunge_all()
    task_id = kwargs['task_id']
    task = DesktopTask.query.filter_by(id=task_id).first()
    if not task:
        LOG.warning('Could not wait desktop for task %s, task not exists' % task_id)
        return
    db.session.refresh(task)
    if task.stage == TaskState.FINISHED or task.stage != 'FLOATING':
        LOG.warning('Skip floating for %r, task finished or not in floating stage' % task)
        return
    LOG.info('Floating for %r' % task)
    LOG.debug('Task context: %r' % task.context)
    instance_id = task['vm']

    try:
        floating_ip = network.associate_floating_ip(instance_id)
        task['floating_ip'] = floating_ip
        task.record_stage()
        task.go_next()
        db.session.add(task)
        if task.get('desktop'):
            desktop = Desktop.query.filter_by(id=task['desktop']).first()
            if desktop is not None:
                desktop.floating_ip = floating_ip
                desktop.need_floating = False
                db.session.add(desktop)
        db.session.commit()
        LOG.info('Associate floating ip success, instance id: %s' % instance_id)
        LOG.debug('Task context: %r' % task.context)
    except Exception as ex:
        LOG.exception('Unable to associate a floating ip for %r' % task)
        task.record_stage(False)
        task.retries += 1
        db.session.add(task)
        db.session.commit()
        if task.retries >= 3:
            LOG.error('Failed to associate a floating ip, too many retries')
            task.go_error()
        else:
            raise self.retry(exc=ex)


@celery.task(name='detect_floating', bind=True, max_retries=None, default_retry_delay=20)
def detect_floating(self, *args, **kwargs):
    db.session.expunge_all()
    task_id = kwargs['task_id']
    task = DesktopTask.query.filter_by(id=task_id).first()
    if not task:
        LOG.warning('Could not detect floating for task %s, task not exists' % task_id)
        return
    db.session.refresh(task)
    if task.stage == TaskState.FINISHED or task.stage != 'DETECT':
        LOG.warning('Skip detect for %r, task finished or not in detect stage' % task)
        return
    LOG.info('Detect for %r' % task)
    LOG.debug('Task context: %r' % task.context)

    # first time?
    if task.get('detect_started_at') is None:
        task['detect_started_at'] = datetime.datetime.now().isoformat()
    if task.get('detect_timeout') is None:
        task['detect_timeout'] = 5*60
    db.session.add(task)
    db.session.commit()

    detect_method = task['detect_method']
    floating_ip = task.get('floating_ip')
    if floating_ip is None:
        LOG.error('Detect for %r, no floating ip' % task)
        task.go_error()
        return

    # detect
    if detect_method == 'PING':
        from phoenix.common.ping import ping
        try:
            result = ping(floating_ip)
        except Exception as ex:
            LOG.exception('Detect(ping) for %r, fail' % task)
            task.retries += 1
            if task.retries >= 3:
                LOG.error('Failed to detect floating ip for %r, too many retires' % task)
                return
            else:
                raise self.retry(exc=ex)
        if result:
            LOG.info('Detect for %r, success' % task)
            task.record_stage()
            task.go_next()
            desktop = Desktop.query.filter_by(id=task['desktop']).first()
            desktop.go_active()
        else:
            now = datetime.datetime.now()
            started_at = iso8601.parse_date(task['detect_started_at'], None)
            if (now - started_at).seconds > task['detect_timeout']:
                LOG.error('Failed to detect floating ip for %r, timeout' % task)
                task.record_stage(False, 'Timeout')
                task.go_error()
                return
            else:
                raise self.retry(exc=None)
    else:
        LOG.error('Detect for %r, unknown detect method' % task)
        task.record_stage(False, 'Unknown detect method')
        task.go_error()


@celery.task(name='set_desktop_state', bind=True)
def set_desktop_state(self, *args, **kwargs):
    db.session.expunge_all()
    task_id = kwargs['task_id']
    task = DesktopTask.query.filter_by(id=task_id).first()
    if not task:
        LOG.warning('Could not set desktop state for task %s, task not exists' % task_id)
        return
    db.session.refresh(task)
    if task.state != TaskState.FINISHED:
        LOG.warning('Could not set desktop state for %r, task not finished' % task)
        return
    desktop = Desktop.query.filter_by(id=task.get('desktop')).first()
    if not desktop:
        LOG.warning('Could not set desktop state for %r, desktop not exists' % task)
        return
    if task.get('desktop_state_map'):
        desktop.desktop_state = task['desktop_state_map'][task.result]
    else:
        desktop.desktop_state = DesktopState.ACTIVE
    db.session.add(desktop)
    db.session.commit()


@celery.task(name='delete_desktop', bind=True, max_retries=3, default_retry_delay=10)
def delete_desktop(self, *args, **kwargs):
    db.session.expunge_all()
    task_id = kwargs['task_id']
    task = DesktopTask.query.filter_by(id=task_id).first()
    if not task:
        LOG.warning('Could not delete desktop for task %s, task not exists' % task_id)
        return
    db.session.refresh(task)
    if task.state == TaskState.FINISHED or task.stage != 'DELETE':
        LOG.warning('Could not delete desktop for %r, task finished or not in delete stage' % task)
        return
    desktop = Desktop.query.filter_by(id=task.get('desktop')).first()
    if desktop is None:
        LOG.warning('Could not delete desktop for %r, desktop %s not exists' % (task, task.get('desktop')))
        return
    LOG.info('Delete desktop for %r' % task)
    LOG.debug('Task context: %r' % task.context)

    from novaclient.exceptions import NotFound

    try:
        if desktop.vm_ref is not None:
            # TODO need to release floating ip
            compute.delete_server(desktop.vm_ref)
            network.disassociate_floating_ip(desktop.vm_ref)
        Desktop.query.filter_by(id=desktop.id).delete()
        task.go_next()
        LOG.info('Delete desktop for %r, success' % task)
    except NotFound as ex:
        LOG.warning('VM %s of desktop %r not found' % (desktop.vm_ref, desktop))
        Desktop.query.filter_by(id=desktop.id).delete()
        task.go_next()
        db.session.commit()
    except Exception as ex:
        LOG.exception('Unable to delete desktop for %r' % task)
        task.retries += 1
        if task.retries >= 3:
            LOG.error('Failed to delete desktop for %r, too many retries')
            task.go_error()
        db.session.add(task)
        db.session.commit()
        if task.retries < 3:
            raise self.retry(exc=ex)


def create_desktop_detect(task_id):
    db.session.flush()
    _create_desktop_detect.apply_async(kwargs={'task_id': task_id}, countdown=1)


@celery.task(name='_create_desktop_detect', bind=True, max_retries=None, default_retry_delay=10)
def _create_desktop_detect(self, *args, **kwargs):
    task_id = kwargs['task_id']
    desktop_task = DesktopTask.query.filter_by(id=task_id).first()
    if not desktop_task:
        LOG.warning('Could not detect static desktop state, task %s not found' % task_id)
        return
    if desktop_task.state != TaskState.FINISHED:
        LOG.debug('Detect static desktop state for %r, not finished' % desktop_task)
        raise self.retry(exc=None)
    if desktop_task.result == TaskResult.ERROR:
        LOG.error("Detect static desktop(task_id: %s) failed" % task_id)


def run_migrationtask(task_id, link=None, link_error=None):
    task = DesktopTask.query.filter_by(id=task_id).first()
    if not task:
        LOG.warning('Could not migrate/evacuate desktop for task %s, task not exists' % task_id)
        return
    sub_tasks = []
    stage_chain = json.loads(task.stage_chain)
    for stage in stage_chain[stage_chain.index(task.stage):]:
        if stage == 'MIGRATE':
            sub_tasks.append(migrate_desktop.s(task_id=task_id))
        elif stage == 'EVACUATE':
            sub_tasks.append(evacuate_desktop.s(task_id=task_id))
        elif stage == 'WAIT':
            sub_tasks.append(wait_desktop.s(task_id=task_id))
        elif stage == 'DETECT':
            sub_tasks.append(detect_floating.s(task_id=task_id))
        elif stage == "DISASSOCIATE":
            sub_tasks.append((disassociate_floating.s(task_id=task_id)))
        elif stage == 'FLOATING':
            sub_tasks.append(assign_floating.s(task_id=task_id))

    c = chain(*sub_tasks)
    if link:
        c.link(set_desktop_state.s(task_id=task_id) | link)
    else:
        c.link(set_desktop_state.s(task_id=task_id))
    if link_error:
        c.link_error(set_desktop_state.s(task_id=task_id) | link_error)
    else:
        c.link_error(set_desktop_state.s(task_id=task_id))
    c.apply_async(countdown=1)


@celery.task(name='migrate_desktop', bind=True, max_retries=3, default_retry_delay=10)
def migrate_desktop(self, *args, **kwargs):
    task_id = kwargs['task_id']
    task = DesktopTask.query.filter_by(id=task_id).first()
    if not task:
        LOG.warning('Could not migrate desktop for task %s, task not exists' % task_id)
        return
    db.session.refresh(task)
    if task.stage == TaskState.FINISHED or task.stage != 'MIGRATE':
        LOG.warning('Skip migrate for %r, task finished or not in migrate stage' % task)
        return
    LOG.info('Migrate desktop for %r' % task)
    LOG.debug('Task context: %r' % task.context)

    # update a desktop which need be rebuild
    desktop = Desktop.query.filter_by(id=task['desktop']).first()
    desktop.desktop_state = DesktopState.MIGRATING
    db.session.add(desktop)
    db.session.commit()
    task.state = TaskState.RUNNING
    db.session.add(task)
    db.session.commit()

    destination_host = task['destination_host']
    vm = compute.get_server(desktop.vm_ref)

    # migrate a vm
    try:
        AdminCompute.live_migrate_server(server=vm,host=destination_host,block_migration=False,disk_over_commit=False)
        db.session.add(desktop)
        task['vm'] = desktop.vm_ref
        task.record_stage()
        task.go_next()
        db.session.commit()
        LOG.info('Migrate desktop for %r, success' % task)
        LOG.debug('Task context: %r' % task.context)
    except Exception as ex:
        LOG.exception('Unable to migrate a desktop for %r' % task)
        task.record_stage(False)
        task.retries += 1
        db.session.add(task)
        db.session.commit()
        if task.retries >= 3:
            LOG.error('Failed to migrate a desktop, too many retries')
            task.go_error()
            desktop.desktop_state = DesktopState.ERROR
            db.session.add(desktop)
            db.session.commit()
        else:
            raise self.retry(exc=ex)


@celery.task(name='evacuate_desktop', bind=True, max_retries=3, default_retry_delay=10)
def evacuate_desktop(self, *args, **kwargs):
    task_id = kwargs['task_id']
    task = DesktopTask.query.filter_by(id=task_id).first()
    if not task:
        LOG.warning('Could not evacuate desktop for task %s, task not exists' % task_id)
        return
    db.session.refresh(task)
    if task.stage == TaskState.FINISHED or task.stage != 'EVACUATE':
        LOG.warning('Skip evacuate for %r, task finished or not in evacuate stage' % task)
        return
    LOG.info('Evacuate desktop for %r' % task)
    LOG.debug('Task context: %r' % task.context)

    # update a desktop which need be rebuild
    desktop = Desktop.query.filter_by(id=task['desktop']).first()
    desktop.desktop_state = DesktopState.EVACUATING
    db.session.add(desktop)
    db.session.commit()
    task.state = TaskState.RUNNING
    db.session.add(task)
    db.session.commit()

    destination_host = task['destination_host']
    vm = compute.get_server(desktop.vm_ref)

    # migrate a vm
    try:
        AdminCompute.evacuate_server(server=vm,host=destination_host)
        db.session.add(desktop)
        task['vm'] = desktop.vm_ref
        task.record_stage()
        task.go_next()
        db.session.commit()
        LOG.info('Evacuate desktop for %r, success' % task)
        LOG.debug('Task context: %r' % task.context)
    except Exception as ex:
        LOG.exception('Unable to evacuate a desktop for %r' % task)
        task.record_stage(False)
        task.retries += 1
        db.session.add(task)
        db.session.commit()
        if task.retries >= 3:
            LOG.error('Failed to evacuate a desktop, too many retries')
            task.go_error()
            desktop.desktop_state = DesktopState.ERROR
            db.session.add(desktop)
            db.session.commit()
        else:
            raise self.retry(exc=ex)


@celery.task(name='disassociate_floating', bind=True, max_retries=3, default_retry_delay=10)
def disassociate_floating(self, *args, **kwargs):
    task_id = kwargs['task_id']
    task = DesktopTask.query.filter_by(id=task_id).first()
    if not task:
        LOG.warning('Could not disassociate floating for task %s, task not exists' % task_id)
        return
    db.session.refresh(task)
    if task.stage == TaskState.FINISHED or task.stage != 'DISASSOCIATE':
        LOG.warning('Skip disassociate for %r, task finished or not in disassociate stage' % task)
        return
    LOG.info('Disassociate floating for %r' % task)
    LOG.debug('Task context: %r' % task.context)

    # update a desktop which need be rebuild
    desktop = Desktop.query.filter_by(id=task['desktop']).first()
    desktop.desktop_state = DesktopState.EVACUATING
    db.session.add(desktop)
    db.session.commit()
    task.state = TaskState.RUNNING
    db.session.add(task)
    db.session.commit()

    vm = compute.get_server(desktop.vm_ref)

    # disassociate floating ip
    try:
        network.disassociate_floating_ip(vm)
        if task.get('desktop'):
            desktop = Desktop.query.filter_by(id=task['desktop']).first()
            if desktop is not None:
                desktop.floating_ip = None
                desktop.need_floating = True
                db.session.add(desktop)
        db.session.commit()
        task['vm'] = desktop.vm_ref
        task.record_stage()
        task.go_next()
        db.session.commit()
        LOG.info('Disassociate desktop for %r, success' % task)
        LOG.debug('Task context: %r' % task.context)
    except Exception as ex:
        LOG.exception('Unable to disassociate a desktop for %r' % task)
        task.record_stage(False)
        task.retries += 1
        db.session.add(task)
        db.session.commit()
        if task.retries >= 3:
            LOG.error('Failed to disassociate a desktop, too many retries')
            task.go_error()
            desktop.desktop_state = DesktopState.ERROR
            db.session.add(desktop)
            db.session.commit()
        else:
            raise self.retry(exc=ex)
