# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# comment
#
# 2016/4/12 qinjinghui : Init
__author__ = 'qinjinghui'

import datetime
import time
import logging
import json
import iso8601
from flask import render_template, request, jsonify, current_app, redirect, url_for, flash
from flask.ext.login import login_user, login_required, logout_user, current_user
from flask.ext import excel
import pyexcel.ext.xls
import pyexcel.ext.xlsx

from . import desktop
from ..setting.forms import ParamForm
from ...models import Parameter, Permission, Desktop, Course, DesktopType, \
    DesktopState, User,DesktopTask, TaskState,TaskResult,\
    Image, Flavor
from . import utils
from ..image.utils import get_instance_console
from ... import db
from ... import app
from sqlalchemy import or_
from .forms import CreateStaticDesktopForm, FileUploadForm
from ...jinja_filters import datetime_format
from ..log.utils import UserActionLogger
from ...common import imageutils
from ...audit import ResourceController

from phoenix.cloud import image as OpenstackImageService
from phoenix.cloud import compute as OpenstackComputeService
from phoenix.cloud import network as OpenstackNetworkService

LOG = logging.getLogger(__name__)
ua_logger = UserActionLogger()

def get_user_permission(user):
    return user.role.permissions


def get_course_flavor_dict():
    flavor_dict = {}
    try:
        course_list = Course.query.all()
        for course in course_list:
            flavor = OpenstackComputeService.get_flavor(course.flavor_ref)
            flavor_dict[course.id] = "%dCPU | %dM RAM | %dG Disk" % \
                                     (flavor.vcpus, flavor.ram, flavor.disk)
        return flavor_dict
    except:
        LOG.exception("Get Course Flavor Dict Failed.")
        return {}


def get_course_image_dict():
    image_dict = {}
    try:
        course_list = Course.query.all()
        for course in course_list:
            image = OpenstackImageService.get_image(course.image_ref)
            image_dict[course.id] = image.name
        return image_dict
    except:
        LOG.exception("Get Course Image Dict Failed.")
        return {}


def get_flavor_by_vmid(vmid):
    try:
        vm = OpenstackComputeService.get_server(vmid)
        flavor = OpenstackComputeService.get_flavor(vm.flavor['id'])
        return "%dCPU | %dM RAM | %dG Disk" % \
               (flavor.vcpus, flavor.ram, flavor.disk)
    except:
        LOG.exception("Get Flavor By VM Id Failed.")
        return ""


def get_imagename_by_vmid(vmid):
    try:
        vm = OpenstackComputeService.get_server(vmid)
        image = OpenstackImageService.get_image(vm.image['id'])
        return image.name
    except:
        LOG.exception("Get Image Name By VM Id Failed." )
        return ""


def get_imagename_by_imageid(image_id):
    try:
        image = OpenstackImageService.get_image(image_id)
        return image.name
    except:
        LOG.exception("Get Image Name By Image Id Failed.")
        return ""


@desktop.route("/course_desktop", methods=['GET'])
@login_required
def course_desktop():
    desktop_list = []
    image_dict = get_course_image_dict()
    flavor_dict = get_course_flavor_dict()
    course_list = Course.query.filter_by(owner_id=current_user.id).all()
    for course in course_list:
        course_desktop_list = Desktop.query.filter_by(
            course_id=course.id, desktop_type=DesktopType.COURSE).all()
        for vm_desktop in course_desktop_list:
            db.session.refresh(vm_desktop)
            desktop_info = {
                "id": vm_desktop.id,
                "name": vm_desktop.name,
                "vmid": vm_desktop.vm_ref,
                "owner_id": vm_desktop.owner_id,
                "size": flavor_dict.get(vm_desktop.course_id, ""),
                "image_name": image_dict.get(vm_desktop.course_id, ""),
                "ip": vm_desktop.floating_ip,
                "destroy_time": datetime_format(vm_desktop.end_datetime),
                "status_chs": DesktopState.get_state_chs(
                    vm_desktop.desktop_state) if vm_desktop.desktop_state
                               else "创建中",
                "status": vm_desktop.desktop_state,
                "can_rebuild": vm_desktop.can_rebuild(),
                "can_rent_or_snap": vm_desktop.can_rent_or_snap(),
            }
            desktop_list.append(desktop_info)
    return render_template('teachers/desktop/course_desktop.html',
                       desktop_list=desktop_list)



@desktop.route("/course_desktop_table", methods=['GET','POST'])
def course_desktop_table():
    # 列号对应的排序属性
    col_map = {
        "0": "name",
        "1": "owner_id",
        "2": "size",
        "3": "image_name",
        "4": "ip",
        "5": "status_chs",
        "6": "destroy_time",
        "7": "operation",
    }

    attr_map = {
        "name": "name",
        "owner_id": "owner_id",
        "ip":"floating_ip",
        "destroy_time": "end_datetime"
    }

    sEcho = request.args.get('sEcho', "1")
    iDisplayStart = request.args.get("iDisplayStart", "0")
    iDisplayLength = request.args.get("iDisplayLength", "10")
    sSearch = request.args.get("sSearch", '')
    iSortCol = request.args.get("iSortCol_0", '0')
    sSortDir = request.args.get("sSortDir_0", '')
    if iSortCol is None:
        iSortCol = '1'
    if sSortDir is None:
        sSortDir = "desc"
    sort_col = col_map[iSortCol]

    user_permission = get_user_permission(current_user)
    if sSearch == '' or sSearch is None:
        if current_user.is_administrator():
            query = Desktop.query.filter_by(desktop_type=DesktopType.COURSE)
        elif user_permission == Permission.COURSE | Permission.DESKTOP:
            courses = Course.query.filter_by(owner_id=current_user.id)
            query = Desktop.query.filter_by(owner_id=0)
            for course in courses:
                query_desktop = Desktop.query.filter_by(desktop_type=DesktopType.COURSE, course_id=course.id)
                query = query.union(query_desktop)
        else:
            query = Desktop.query.filter_by(desktop_type=DesktopType.COURSE, owner_id=current_user.id)

    else:
        if current_user.is_administrator():
            query = Desktop.query.filter_by(desktop_type=DesktopType.COURSE).filter(or_(Desktop.name.like("%" +sSearch +"%"),Desktop.floating_ip.like("%"+sSearch + "%")))

            users = User.query.filter(User.username.like("%" + sSearch + "%"))
            for user in users:
                query_desktop = Desktop.query.filter_by(owner_id=user.id,desktop_type=DesktopType.COURSE)
                query = query.union(query_desktop)
        elif user_permission == Permission.COURSE | Permission.DESKTOP:
            courses = Course.query.filter_by(owner_id=current_user.id)
            query = Desktop.query.filter_by(owner_id=0)
            for course in courses:
                query_desktop = Desktop.query.filter_by(desktop_type=DesktopType.COURSE, course_id=course.id)
                query = query.union(query_desktop)
            query = query.filter(or_(Desktop.name.like("%" + sSearch + "%"),
                    Desktop.floating_ip.like("%" + sSearch + "%")))
        else:
            query = Desktop.query.filter_by(desktop_type=DesktopType.COURSE, owner_id=current_user.id).filter(or_(Desktop.name.like("%" + sSearch + "%"),
                    Desktop.floating_ip.like("%" + sSearch + "%")))

    #query = query.distinct(Desktop.id)
    if attr_map.get(sort_col):
        sort_col = getattr(Desktop, attr_map[sort_col])
    else:
        sort_col = getattr(Desktop, sort_col)
    if sSortDir == "desc":
        query = query.order_by(sort_col.desc())
    else:
        query = query.order_by(sort_col.asc())

    page = int(iDisplayStart) // int(iDisplayLength)
    pagination = query.paginate(page + 1, int(iDisplayLength), False)
    desktop_list = pagination.items
    desktop_json_list = []
    for item in desktop_list:
        image = Image.query.filter_by(ref_id=item.image_ref).first()
        if image:
            imagename = image.name
        else:
            imagename = get_imagename_by_vmid(item.vm_ref)

        flavor = Flavor.query.filter_by(ref_id=item.flavor_ref).first()
        if flavor:
            flavorname = flavor.description
        else:
            flavorname = get_flavor_by_vmid(item.vm_ref)
        desktop_json_list.append(
            {
                'id': item.id,
                "name": {
                    "vmid": item.vm_ref,
                    "owner_id": item.owner.username if item.owner else "无人占用",
                    "name": item.name,
                    "desktop_id": item.id,
                },
                "owner": {
                    "owner_id": item.owner.username if item.owner else "无人占用",
                    "desktop_id": item.id,
                },
                "size": flavorname,
                "image_name": imagename,
                "ip": item.floating_ip,
                "status_chs": DesktopState.get_state_chs(item.desktop_state) if
                item.desktop_state else "创建中",
                "destroy_time": datetime_format(item.end_datetime),
                "operation": {
                    'id': item.id,
                    "vmid": item.vm_ref,
                    "name": item.name,
                    "owner": item.owner.username if item.owner else "无人占用",
                    "course": item.course_id,
                    "status": item.desktop_state if item.desktop_state else
                    item.vm_state,
                    "can_rebuild": item.can_rebuild(),
                    "can_rent_or_snap": item.can_rent_or_snap(),
                    "can_reboot_or_del": item.can_reboot_or_del(),
                    "can_poweroff": item.can_power_off(),
                    "can_poweron": item.can_power_on(),
                },
            }
        )

    data = {"sEcho": sEcho,
            "iTotalRecords": str(pagination.total),
            "iTotalDisplayRecords": str(pagination.total),
            "aaData": desktop_json_list
            }
    db.session.remove()
    return jsonify(data)


@desktop.route('/course_desktop', methods=['DELETE'])
def delete_desktops():
    """ Delete course desktop
    """
    request_json = request.json
    force = request_json.get('force', False)
    desktops = request_json.get('desktops')
    result = {
        'status': 'success',
        'data': {
            'normal': [],
            'force': []
        },
    }
    for d in desktops:
        desktop = Desktop.query.filter_by(id=d).first()
        if desktop is not None:
            if desktop.vm_ref is not None:
                deleted = False
                for i in range(3):
                    try:
                        OpenstackComputeService.delete_server(desktop.vm_ref)
                        deleted = True
                        break
                    except Exception as ex:
                        LOG.exception("Unable to delete vm %s of desktop %s in cloud, will try again" % (desktop.vm_ref, desktop))
                if deleted:
                    LOG.info("VM %s of desktop %s had been deleted" % (desktop.vm_ref, desktop))
                    db.session.delete(desktop)
                    ua_logger.info(current_user, "桌面 %s 的VM %s 已被删除" % (desktop.name, desktop.vm_ref))
                    result['data']['normal'].append(desktop.id)
                elif force:
                    LOG.warn("Unable to delete vm %s of desktop %s but force delete the desktop" % (desktop.vm_ref, desktop))
                    db.session.delete(desktop)
                    ua_logger.info(current_user, "无法删除桌面 %s 的VM %s, 从数据库中强行删除桌面" % (desktop.name, desktop.vm_ref))
                    result['data']['force'].append(desktop.id)
            else:
                db.session.delete(desktop)
                LOG.warning('Desktop %r had been deleted' % desktop)
                result['data']['normal'].append(desktop.id)
    return jsonify(result)


@desktop.route("/static_desktop", methods=['GET'])
@login_required
def static_desktop():
    return render_template('teachers/desktop/static_desktop.html')


@desktop.route("/static_desktop_table", methods=['GET','POST'])
def static_desktop_table():
    # 列号对应的排序属性
    col_map = {"0": "id",
               "1": "name",
               "2": "owner_id",
               "3": "size",
               "4": "image_name",
               "5": "ip",
               "6": "status_chs",
               "7": "operation",
                }

    attr_map = {
        "name": "name",
        "owner_id": "owner_id",
        "ip":"floating_ip",
    }

    sEcho = request.args.get('sEcho', "1")
    iDisplayStart = request.args.get("iDisplayStart", "0")
    iDisplayLength = request.args.get("iDisplayLength", "10")
    sSearch = request.args.get("sSearch", '')
    iSortCol = request.args.get("iSortCol_0", '0')
    sSortDir = request.args.get("sSortDir_0", '')
    if iSortCol is None:
        iSortCol = '1'
    if sSortDir is None:
        sSortDir = "desc"
    sort_col = col_map[iSortCol]

    if sSearch == '' or sSearch is None:
        if (current_user.is_administrator()):
            query = Desktop.query.filter_by(desktop_type=DesktopType.STATIC)
        else:
            query = Desktop.query.filter_by(desktop_type=DesktopType.STATIC,
                                            owner_id=current_user.id)
    else:
        if (current_user.is_administrator()):
            query = Desktop.query.filter_by(desktop_type=DesktopType.STATIC).filter(or_(Desktop.name.like("%" + sSearch + "%"), Desktop.floating_ip.like("%" + sSearch + "%")))

            users = User.query.filter(User.username.like("%" + sSearch + "%"))
            for user in users:
                query_desktop = Desktop.query.filter_by(owner_id=user.id,desktop_type=DesktopType.STATIC)
                query = query.union(query_desktop)
        else:
            query = Desktop.query.filter_by(desktop_type=DesktopType.STATIC, owner_id=current_user.id).filter(or_(Desktop.name.like("%" + sSearch + "%"),
                    Desktop.floating_ip.like("%" + sSearch + "%")))

    if attr_map.get(sort_col):
        sort_col = getattr(Desktop, attr_map[sort_col])
    else:
        sort_col = getattr(Desktop, sort_col)
    if sSortDir == "desc":
        query = query.order_by(sort_col.desc())
    else:
        query = query.order_by(sort_col.asc())

    page = int(iDisplayStart) // int(iDisplayLength)
    pagination = query.paginate(page + 1, int(iDisplayLength), False)
    desktop_list = pagination.items
    desktop_json_list = []
    for item in desktop_list:
        image = Image.query.filter_by(ref_id=item.image_ref).first()
        if image:
            imagename = image.name
        else:
            imagename = get_imagename_by_vmid(item.vm_ref)

        flavor = Flavor.query.filter_by(ref_id=item.flavor_ref).first()
        if flavor:
            flavorname = flavor.description
        else:
            flavorname = get_flavor_by_vmid(item.vm_ref)
        desktop_json_list.append(
            {
                "id": item.vm_ref,
                "name":{
                    "vmid": item.vm_ref,
                    "owner_id":item.owner.username if item.owner else "无人占用",
                    "name":item.name,
                },
                "owner_id":item.owner.username if item.owner else "无人占用",
                "size":flavorname,
                "image_name":imagename,
                "ip":item.floating_ip,
                "status_chs":DesktopState.get_state_chs(item.desktop_state) if
                item.desktop_state else "创建中",
                "operation":{
                    "vmid" : item.vm_ref,
                    "name": item.name,
                    "status" : item.desktop_state if item.desktop_state else
                    item.vm_state,
                    "can_rebuild": item.can_rebuild(),
                    "can_rent_or_snap": item.can_rent_or_snap(),
                    "can_reboot_or_del": item.can_reboot_or_del(),
                    "can_poweroff": item.can_power_off(),
                    "can_poweron": item.can_power_on(),
                },
            }
        )

    data = {"sEcho": sEcho,
            "iTotalRecords": str(pagination.total),
            "iTotalDisplayRecords": str(pagination.total),
            "aaData": desktop_json_list
            }
    db.session.remove()
    return jsonify(data)

@desktop.route("/free_desktop", methods=['GET'])
def free_desktop():
    free_desktop_switch = Parameter.query.filter_by(
        name="free_desktop_switch").first()
    free_desktop_capacity = Parameter.query.filter_by(
        name="free_desktop_capacity").first()
    free_desktop_flavor = Parameter.query.filter_by(
        name="free_desktop_flavor").first()
    free_desktop_image = Parameter.query.filter_by(
        name="free_desktop_image").first()
    free_desktop_start_time = Parameter.query.filter_by(
        name="free_desktop_start_time").first()
    free_desktop_stop_time = Parameter.query.filter_by(
        name="free_desktop_stop_time").first()
    data = {free_desktop_switch.name: free_desktop_switch.get_value(),
            free_desktop_capacity.name: free_desktop_capacity.get_value(),
            free_desktop_flavor.name: free_desktop_flavor.get_value(),
            free_desktop_image.name: free_desktop_image.get_value(),
            free_desktop_start_time.name: free_desktop_start_time.get_value(),
            free_desktop_stop_time.name: free_desktop_stop_time.get_value()
            }
    # free_desktop_param_form = ParamForm(data)
    free_desktop_param_form = ParamForm()
    free_desktop_param_form.free_desktop_switch.data = free_desktop_switch.get_value()
    free_desktop_param_form.free_desktop_capacity.data = free_desktop_capacity.get_value()
    free_desktop_param_form.free_desktop_flavor.data = free_desktop_flavor.get_value()
    free_desktop_param_form.free_desktop_image.data = free_desktop_image.get_value()
    free_desktop_param_form.free_desktop_start_time.data = datetime.datetime.strptime(
        free_desktop_start_time.get_value(), "%H:%M")
    free_desktop_param_form.free_desktop_stop_time.data = datetime.datetime.strptime(
        free_desktop_stop_time.get_value(), "%H:%M")

    desktop_list = []
    free_desktop_list = Desktop.query.filter_by(
        desktop_type=DesktopType.FREE).all()
    for vm_desktop in free_desktop_list:
        user = User.query.filter_by(id=vm_desktop.owner_id).first()
        desktop_info = {
            "name": vm_desktop.name,
            "vmid": vm_desktop.vm_ref,
            "owner_id": user.username,
            "size": get_flavor_by_vmid(vm_desktop.vm_ref),
            "image_name": get_imagename_by_vmid(vm_desktop.vm_ref),
            "ip": vm_desktop.floating_ip,
            "destroy_time": vm_desktop.end_datetime.strftime("%H:%M"),
            "status_chs": DesktopState.get_state_chs(vm_desktop.vm_state),
            "status": vm_desktop.vm_state,
            "can_rebuild": vm_desktop.can_rebuild(),
            "can_rent_or_snap": vm_desktop.can_rent_or_snap(),
        }
        desktop_list.append(desktop_info)

    return render_template('teachers/desktop/free_desktop.html',
                           form=free_desktop_param_form,
                           free_desktop_list=desktop_list)


@desktop.route("/desktop_console", methods=['GET', 'POST'])
def desktop_console():
    try:
        vmid = request.values.get("id", "")
        vm_desktop = Desktop.query.filter_by(vm_ref=vmid).first()
        # if vm_desktop:
        #     print("vm_desktop exist.")
        if vm_desktop.owner_id:
            vm_owner = vm_desktop.owner.username
        else:
            vm_owner = "无人占用"
        vm_name = vm_desktop.name
        vm_ip = vm_desktop.floating_ip
        vm_state = DesktopState.get_state_chs(vm_desktop.vm_state)
        vm_config = get_flavor_by_vmid(vm_desktop.vm_ref)
        console = get_instance_console(vm_desktop.vm_ref)
    except:
        LOG.exception("Get Desktop Console Failed: %s" % vmid)
        console = None
        vm_name = None
        vm_config = None
        vm_ip = None
        vm_state = None
        vm_owner = None
    return render_template('teachers/desktop/desktop_console.html', console=console,
                           vm_name=vm_name, vm_config=vm_config, vm_ip=vm_ip,
                           vm_state=vm_state, vm_owner=vm_owner)


@desktop.route("/add_time_by_vm", methods=['POST'])
def add_time_by_vm():
    result = {}
    result['status'] = "fail"
    try:
        vmid = request.values.get("hide_vmid", "")
        mins = request.values.get("add_time")
        if mins.isdigit():
            seconds = int(mins) * 60
            vm_desktop = Desktop.query.filter_by(vm_ref=vmid).first()
            vm_desktop.delay(seconds)
            ua_logger.info(current_user, '将桌面(%s)的回收时间延迟了%s分钟' % (vm_desktop.name, mins))
            LOG.info('将桌面(%s)的回收时间延迟了%s分钟' % (vm_desktop.name, mins))
            result['status'] = "success"
    except Exception as ex:
        LOG.exception("Delay failed for desktop %s" % vmid)
        result['status'] = "fail"
    return jsonify(**result)


@desktop.route("/refresh_state", methods=['POST'])
def refresh_state():
    pass


@desktop.route("/supply", methods=['POST'])
def supply_desktop():

    result_json = {
        'status': 'success',
        'data': {}
    }
    parameters = request.json
    course_id = parameters['course_id']
    count = parameters['count']

    desktop_count_validator = utils.DesktopCountValidator()
    if not desktop_count_validator.validate(count):
        LOG.error('Supply %s desktop for course with id %s fail, parameter format error' % (count, course_id))
        result_json['status'] = 'fail'
        result_json['data'] = 'parameter format error'

    try:
        course = Course.query.filter_by(id=course_id).first()
        if course:
            try:
                actual_count = ResourceController().supply_max_desktop_count(course, count)
                if actual_count <= 0:
                    result_json['status'] = 'fail'
                    result_json['data'] = 'resource exceed system limit'
                elif actual_count < count:
                    course.supply_desktops(actual_count)
                    result_json['status'] = 'fail'
                    result_json['data']['msg'] = 'part exceed system limit'
                    result_json['data']['actual_count'] = actual_count
                else:
                    course.supply_desktops(actual_count)
                    LOG.info('Supply %s desktops for course %s' % (count, course.name))
                    ua_logger.info(current_user, "为课程 %s 补充桌面 %s 个" % (course.name, count))
            except:
                LOG.exception('Supply desktop for course %s fail' % course.name)
                result_json['status'] = 'fail'
                result_json['data'] = 'no current lesson'
        else:
            ua_logger.info(current_user, "为课程 %s 补充 %s 桌面失败，课程不存在" % (course.name, count))
            LOG.error('Supply %s desktop for course %s fail, course not exist' % (count, course.name))
            result_json['status'] = 'fail'
            result_json['data'] = 'course not exist'
    except:
        LOG.exception('Supply desktop for course with id %s fail' % course_id)
        result_json['status'] = 'error'
        result_json['data'] = 'server error'

    return jsonify(result_json)


@desktop.route("/delete_fudp_desktops", methods=['POST'])
def delete_free_desktops():
    pass


@desktop.route("/reboot_vm", methods=['POST'])
def reboot_vm():
    """
    重启桌面
    :return:
    """
    vmid = request.values.get("vmid", "")
    result = {}
    result['status'] = "fail"
    if vmid:
        try:
            vm_desktop = Desktop.query.filter_by(vm_ref=vmid).first()
            if not vm_desktop:
                result['status'] = "Notexist"
            else:
                if utils.reboot_vm(vmid):
                    ua_logger.info(current_user, "重启桌面: %s" % vm_desktop.name)
                    result['status'] = "success"
                else:
                    result['status'] = "fail"
        except:
            LOG.exception("Reboot VM Failed: %s" % vmid)
            result['status'] = "fail"
    return jsonify(**result)


@desktop.route("/suspend_vm", methods=['POST'])
def suspend_vm():
    """
    关闭/挂起桌面
    :return:
    """
    vmid = request.values.get("vmid","")
    result = {}
    result['status'] = "fail"
    if vmid:
        try:
            vm_desktop = Desktop.query.filter_by(vm_ref=vmid).first()
            if not vm_desktop:
                result['status'] = "Notexist"
            else:
                if utils.suspend_vm(vmid):
                    ua_logger.info(current_user, "关闭桌面: %s" % vm_desktop.name)
                    result['status'] = "success"
                else:
                    result['status'] = "fail"
        except Exception as ex:
            LOG.exception("Suspend VM Failed: %s" % vmid)
            result['status'] = "fail"
    return jsonify(**result)


@desktop.route("/resume_vm", methods=['POST'])
def resume_vm():
    """
    启动桌面
    :return:
    """
    vmid = request.values.get("vmid","")
    result = {}
    result['status'] = "fail"
    if vmid:
        try:
            vm_desktop = Desktop.query.filter_by(vm_ref=vmid).first()
            if not vm_desktop:
                result['status'] = "Notexist"
            else:
                if utils.resume_vm(vmid):
                    ua_logger.info(current_user, "启动桌面: %s" % vm_desktop.name)
                    result['status'] = "success"
                else:
                    result['status'] = "fail"
        except:
            LOG.exception("Resume VM Failed: %s" % vmid)
            result['status'] = "fail"
    return jsonify(**result)


@desktop.route("/rebuild_desktop", methods=["POST"])
def rebuild_desktop():
    """
    还原桌面
    :return:
    """
    vmid = request.values.get("vmid","")
    result = {}
    result['status'] = "fail"
    if vmid:
        try:
            vm_desktop = Desktop.query.filter_by(vm_ref=vmid).first()
            if not vm_desktop:
                result['status'] = "Notexist"
            else:
                if utils.rebuild_vm(vmid):
                    ua_logger.info(current_user, "还原桌面: %s" % vm_desktop.name)
                    result['status'] = "success"
                else:
                    result['status'] = "fail"
        except:
            LOG.exception("Rebuild VM Failed: %s" % vmid)
            result['status'] = "fail"
    return jsonify(**result)


@desktop.route('/desktop_unbunding/<int:id>', methods=['POST'])
@login_required
def unbunding_desktop(id):
    result = {
        'status': 'success',
        'data': {
            'success_id': "",
            'fail_id': "",
            'course_cid': "",
        }
    }
    desktop = Desktop.query.filter_by(id=id).first()
    if desktop:
        if desktop.owner_id != None:
            desktop.owner_id = None
            db.session.add(desktop)
            db.session.commit()
            result['status'] = 'success'
            result['data']['success_id'] = desktop.id
            result['data']['course_cid'] = desktop.course_id
            LOG.debug("桌面 %s 与用户解绑成功" % desktop.id)
            ua_logger.info(current_user, "桌面 %s 与用户解绑" % desktop.id)
        else:
            result['status'] = 'fail'
            result['data']['fail_id'] = desktop.id
            result['data']['course_cid'] = desktop.course_id
            LOG.debug("桌面 %s 与用户解绑失败" % desktop.id)
    else:
        result['status'] = 'fail'
        result['data']['fail_id'] = desktop.id
        result['data']['course_cid'] = desktop.course_id
        LOG.debug("桌面 %s 不存在" % desktop.id)
    return jsonify(result)


@desktop.route('/desktop_binding/<int:id>', methods=['POST'])
@login_required
def binding_desktop(id):
    result = {
        'status': 'success',
        'data': {
            'success_id': "",
            'fail_id': "",
            'success_name': "",
            'fail_name': "",
            'course_cid': "",
        }
    }
    studentbinding = request.json
    desktop = Desktop.query.filter_by(id=id).first()
    if desktop:
        if desktop.owner_id == None:
            if studentbinding == None:
                result['status'] = 'fail'
                result['data']['fail_id'] = desktop.id
                result['data']['course_cid'] = desktop.course_id
                LOG.debug("绑定用户为空")
            else:
                desktop.owner_id = studentbinding
                db.session.add(desktop)
                db.session.commit()
                result['status'] = 'success'
                result['data']['success_id'] = desktop.id
                result['data']['success_name'] = User.query.filter_by(id = desktop.owner_id).first().username
                result['data']['course_cid'] = desktop.course_id
                ua_logger.info(current_user, "桌面 %s 与用户 %s 绑定" % (desktop.id,studentbinding) )
                LOG.debug("桌面 %s 与用户 %s 绑定" % (desktop.id,studentbinding))
        else:
            result['status'] = 'fail'
            result['data']['fail_id'] = desktop.id
            result['data']['course_cid'] = desktop.course_id
            LOG.debug("桌面%s已经与用户绑定" % desktop.id)
    else:
            result['status'] = 'fail'
            result['data']['fail_id'] = desktop.id
            result['data']['course_cid'] = desktop.course_id
            LOG.debug("桌面与用户绑定失败，桌面不存在")
    return jsonify(result)
