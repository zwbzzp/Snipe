# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# comment
#
# 16-8-3 qinjinghui : Init

import heapq
import json
import logging
import simplejson

from flask import render_template, request, jsonify,g, abort
from flask.ext.login import current_user
from flask.ext.login import login_required
from .. import db, celery_tasks
from ..models import HostInfo, Desktop, DesktopType, DesktopState, User, Image, Flavor, DesktopTask, Course, TaskState, StageResult, Desktop, Parameter
from . import vmotion
from .forms import MigrateDesktopForm
from . import utils
from phoenix.cloud.admin import compute as OpenstackComputeService
from phoenix.cloud import image as OpenstackImageService
from ..log.utils import UserActionLogger
from ..auth.principal import admin_permission
from ..jinja_filters import datetime_format
from sqlalchemy import or_

LOG = logging.getLogger(__name__)
ua_logger = UserActionLogger()

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

@vmotion.route('/hostinfo', methods=['GET'])
@login_required
def hostinfo():
    host_info_list = []
    try:
        hypervisors_list = OpenstackComputeService.list_hypervisors(detailed=True)
        hypervisors_dict = {}
        for hypervisor in hypervisors_list:
            hypervisors_dict[hypervisor.hypervisor_hostname] = hypervisor

        services_list = OpenstackComputeService.list_services()
        for service in services_list:
            if service.binary == 'nova-compute':
                hostinfo = HostInfo.query.filter_by(host_name=service.host).first()
                if hostinfo:
                    hostinfo.service_status = service.status
                    db.session.add(hostinfo)
                    db.session.commit()
                else:
                    hostinfo = HostInfo()
                    hostinfo.host_name = service.host
                    hostinfo.zone = service.zone
                    hypervisor = hypervisors_dict.get(hostinfo.host_name, None)
                    if hypervisor:
                        hostinfo.host_ip = hypervisor.host_ip
                        cpu_info = simplejson.loads(hypervisor.cpu_info)
                        hostinfo.cpu_arch = cpu_info['arch']
                        hostinfo.cpu_cores = hypervisor.vcpus
                        hostinfo.mem = hypervisor.memory_mb
                        hostinfo.mem_used = hypervisor.memory_mb_used
                        hostinfo.disk = hypervisor.local_gb
                        hostinfo.disk_used = hypervisor.local_gb_used
                        hostinfo.vms = hypervisor.running_vms

                    hostinfo.service_status = service.status
                    hostinfo.service_state = service.state
                    hostinfo.external_network_state = "up"
                    hostinfo.management_network_state = "up"
                    hostinfo.host_status = "up" if service.state == "up" else "warning"
                    db.session.add(hostinfo)
                    db.session.commit()

        #remove useless hosinfo
        host_info_list = HostInfo.query.all()
        for hostinfo in host_info_list:
            hypervisor = hypervisors_dict.get(hostinfo.host_name, None)
            if not hypervisor:
                db.session.delete(hostinfo)
        db.session.commit()

        host_info_list = HostInfo.query.all()

        vmotion_auto_evacuation = Parameter.query.filter_by(name='vmotion_auto_evacuation').first()
        auto_evacuation_enabled = True if vmotion_auto_evacuation.value == 'on' else False
    except Exception as ex:
        LOG.exception("Get Host Info Failed.")
        abort(500)
    else:
        return render_template('vmotion/hostinfo.html', host_info_list=host_info_list, auto_evacuation_enabled=auto_evacuation_enabled)


@vmotion.route("/update_host_service_status", methods=['PUT'])
@login_required
def update_host_service_status():
    try:
        host_name = request.json.get("host_name")
        service_status = request.json.get("service_status")
        host = HostInfo.query.filter_by(host_name=host_name).first()
        host.service_status = service_status
        if service_status == "enabled":
            OpenstackComputeService.enable_service(host=host_name,binary="nova-compute")
        else:
            OpenstackComputeService.disable_service(host=host_name,binary="nova-compute")
        db.session.add(host)
        db.session.commit()
        return jsonify({'status': 'success',
                        'data': {'host_name': host_name, 'service_status': service_status}})
    except:
        return jsonify({'status': 'fail',
                        'data': 'service not exist'})


@vmotion.route("/update_auto_evacuation_status", methods=['PUT'])
@login_required
def update_auto_evacuation_status():
    try:
        host_name = request.json.get("host_name")
        auto_evacuate = request.json.get("auto_evacuate")
        host = HostInfo.query.filter_by(host_name=host_name).first()
        host.auto_evacuation = True if auto_evacuate == "enabled" else False
        db.session.add(host)
        db.session.commit()
        return jsonify({'status': 'success',
                        'data': {'host_name': host_name, 'auto_evacuate': auto_evacuate}})
    except:
        return jsonify({'status': 'fail',
                        'data': 'exception'})


@vmotion.route("/sync_hostinfo", methods=['GET'])
@login_required
def sync_hostinfo():
    result_json = {
        'status': 'fail',
    }

    try:
        hypervisors_list = OpenstackComputeService.list_hypervisors(
            detailed=True)
        hypervisors_dict = {}
        for hypervisor in hypervisors_list:
            hypervisors_dict[hypervisor.hypervisor_hostname] = hypervisor

        services_list = OpenstackComputeService.list_services()
        for service in services_list:
            if service.binary == 'nova-compute':
                update = True # True means update, False means create
                hostinfo = HostInfo.query.filter_by(
                    host_name=service.host).first()
                if not hostinfo:
                    hostinfo = HostInfo()
                    update = False

                hostinfo.host_name = service.host
                hostinfo.zone = service.zone
                hypervisor = hypervisors_dict.get(hostinfo.host_name, None)
                if hypervisor:
                    hostinfo.host_ip = hypervisor.host_ip
                    cpu_info = simplejson.loads(hypervisor.cpu_info)
                    hostinfo.cpu_arch = cpu_info['arch']
                    hostinfo.cpu_cores = hypervisor.vcpus
                    hostinfo.mem = hypervisor.memory_mb
                    hostinfo.mem_used = hypervisor.memory_mb_used
                    hostinfo.disk = hypervisor.local_gb
                    hostinfo.disk_used = hypervisor.local_gb_used
                    hostinfo.vms = hypervisor.running_vms
                
                hostinfo.service_status = service.status
                if not update:
                    hostinfo.service_state = service.state
                    hostinfo.external_network_state = "up"
                    hostinfo.management_network_state = "up"
                    hostinfo.host_status = "up" if service.state == "up" else "warning"
                db.session.add(hostinfo)
                db.session.commit()

        # remove useless hosinfo
        host_info_list = HostInfo.query.all()
        for hostinfo in host_info_list:
            hypervisor = hypervisors_dict.get(hostinfo.host_name, None)
            if not hypervisor:
                db.session.delete(hostinfo)
        db.session.commit()
        result_json['status'] = 'success'
    except:
        LOG.exception("Sync Host Info Failed.")
        result_json['status'] = 'fail'
    return jsonify(**result_json)


@vmotion.route('/quick_migration', methods=['POST'])
@login_required
def quick_migration():
    src_host_name = request.values.get("src_host_name")
    result = {}
    result["status"] = 'fail'
    result["error_info"] = ""
    result["fail_list"] = []
    try:
        srchost = HostInfo.query.filter_by(host_name = src_host_name).first()
        if not srchost:
            result["status"] = 'fail'
            result["error_info"] = "所选主机不存在"
            return jsonify(**result)

        # Get All back_up host which host_status is up
        backup_host_list = HostInfo.query.filter_by(host_status="up",
                                                        service_status="disabled").filter(HostInfo.host_name != src_host_name).all()
        # Get All online host which host_status is up
        online_host_list = HostInfo.query.filter_by(host_status="up",
                                                        service_status="enabled").filter(HostInfo.host_name != src_host_name).all()

        if len(backup_host_list) == 0 and len(online_host_list) == 0:
            result["status"] = 'fail'
            result["error_info"] = "没有可用的主机以供迁移"
            return jsonify(**result)
        if srchost.host_status == "up":
            #migrate
            if backup_host_list and len(backup_host_list) > 0:
                fail_vm_list = utils.migrate_vms_to_active_hosts(src_host_name, backup_host_list)
                if fail_vm_list and len(fail_vm_list) > 0:
                    fail_vm_list = utils.migrate_vms_to_active_hosts(src_host_name, online_host_list, fail_vm_list)
                    if fail_vm_list and len(fail_vm_list) > 0:
                        # To Do: Send warning to manager
                        ##因内存不足而无法撤离
                        result['status'] = "fail"
                        result["error_info"] = "因内存不足而无法迁移"
                        result['fail_list'] = fail_vm_list
                    else:
                        result['status'] = "success"
                else:
                    result['status'] = "success"
            elif online_host_list and len(online_host_list) > 0:
                fail_vm_list = utils.migrate_vms_to_active_hosts(src_host_name, online_host_list)
                if fail_vm_list and len(fail_vm_list) > 0:
                    # To Do: Send warning to manager
                    # 因内存不足而无法撤离
                    result['status'] = "fail"
                    result["error_info"] = "因内存不足而无法迁移"
                    result['fail_list'] = fail_vm_list
                else:
                    result['status'] = "success"
        elif srchost.external_network_state != "up" and \
                        srchost.management_network_state == "up" and \
                        srchost.service_state == "up":
            if backup_host_list and len(backup_host_list) > 0:
                fail_vm_list = utils.migrate_vms_to_active_hosts(
                    src_host_name, backup_host_list)
                if fail_vm_list and len(fail_vm_list) > 0:
                    fail_vm_list = utils.migrate_vms_to_active_hosts(
                        src_host_name, online_host_list, fail_vm_list)
                    if fail_vm_list and len(fail_vm_list) > 0:
                        # To Do: Send warning to manager
                        ##因内存不足而无法撤离
                        result['status'] = "fail"
                        result["error_info"] = "因内存不足而无法迁移"
                        result['fail_list'] = fail_vm_list
                    else:
                        result['status'] = "success"
                else:
                    result['status'] = "success"
            elif online_host_list and len(online_host_list) > 0:
                fail_vm_list = utils.migrate_vms_to_active_hosts(src_host_name,
                                                                 online_host_list)
                if fail_vm_list and len(fail_vm_list) > 0:
                    # To Do: Send warning to manager
                    # 因内存不足而无法撤离
                    result['status'] = "fail"
                    result["error_info"] = "因内存不足而无法撤离"
                    result['fail_list'] = fail_vm_list
                else:
                    result['status'] = "success"
        elif srchost.external_network_state != "up" and \
                        srchost.management_network_state == "up" and \
                        srchost.service_state != "up":
            result['status'] = 'fail'
            result['error_info'] = "所选主机的计算服务异常，无法迁移"
        elif srchost.external_network_state == "up" and \
                        srchost.management_network_state != "up":
            result['status'] = 'fail'
            result['error_info'] = "所选主机的管理网络异常，无法迁移"
        elif srchost.external_network_state == "up" and \
                        srchost.management_network_state == "up" and \
                        srchost.service_state != "up":
            result['status'] = 'fail'
            result['error_info'] = "所选主机的计算服务异常，无法迁移"
        elif srchost.external_network_state != "up" and \
                        srchost.management_network_state != "up" and \
                        srchost.service_state == "up":
            result['status'] = 'fail'
            result['error_info'] = "所选主机的访问网络及管理网络异常，无法迁移"
        elif srchost.external_network_state != "up" and \
                        srchost.management_network_state != "up" and srchost.service_state != "up":
            #撤离
            if backup_host_list and len(backup_host_list) > 0:
                fail_vm_list = utils.evacuate_vms_to_active_hosts(src_host_name,
                                                                 backup_host_list)
                if fail_vm_list and len(fail_vm_list) > 0:
                    fail_vm_list = utils.evacuate_vms_to_active_hosts(
                        src_host_name, online_host_list, fail_vm_list)
                    if fail_vm_list and len(fail_vm_list) > 0:
                        # To Do: Send warning to manager
                        ##因内存不足而无法撤离
                        result['status'] = "fail"
                        result["error_info"] = "因内存不足而无法迁移"
                        result['fail_list'] = fail_vm_list
                    else:
                        result['status'] = "success"
                else:
                    result['status'] = "success"
            elif online_host_list and len(online_host_list) > 0:
                fail_vm_list = utils.evacuate_vms_to_active_hosts(src_host_name,
                                                                 online_host_list)
                if fail_vm_list and len(fail_vm_list) > 0:
                    # To Do: Send warning to manager
                    # 因内存不足而无法撤离
                    result['status'] = "fail"
                    result["error_info"] = "因内存不足而无法迁移"
                    result['fail_list'] = fail_vm_list
                else:
                    result['status'] = "success"
    except Exception as ex:
        LOG.error("Quick Migrate Failed.")
        result['status'] = 'fail'
    return jsonify(**result)


@vmotion.route('/host_desktop_migration/<string:host_name>', methods=['GET'])
@login_required
def host_desktop_migration(host_name):
    host_list = HostInfo.query.filter_by(host_status="up").filter(
        HostInfo.host_name != host_name).all()

    desktop_list = []
    vm_list = OpenstackComputeService.list_servers(search_opts={'host':host_name})
    for vm in vm_list:
        desktop = Desktop.query.filter_by(vm_ref=vm.id).first()
        if not desktop:
            continue
        flavor = Flavor.query.filter_by(ref_id=desktop.flavor_ref).first()
        if flavor:
            flavorname = flavor.description
        else:
            flavorname = get_flavor_by_vmid(desktop.vm_ref)
        desktop_list.append(
            {
                "id": desktop.vm_ref,
                "name": desktop.name,
                "owner_id": desktop.owner.username if desktop.owner else "无人占用",
                "size": flavorname,
                "host_name": vm.__dict__['OS-EXT-SRV-ATTR:host'],
                "ip": desktop.floating_ip,
                "status_chs": DesktopState.get_state_chs(desktop.desktop_state) if
                desktop.desktop_state else "创建中",
                "can_migrate_or_evacuate": desktop.can_migrate_or_evacuate()
            }
        )

    return render_template('vmotion/host_desktop_migration.html',
                           desktop_list=desktop_list,host_list=host_list)


@vmotion.route('/desktop_migration', methods=['GET'])
@login_required
def desktop_migration():
    host_list = HostInfo.query.filter_by(host_status="up").all()
    return render_template('vmotion/desktop_migration.html',host_list=host_list)


@vmotion.route("/migrate_desktop_table", methods=['GET','POST'])
@login_required
def migrate_desktop_table():
    vm_host_dict = {}
    vm_list = OpenstackComputeService.list_servers()
    for vm in vm_list:
        vm_host_dict[vm.id] = vm.__dict__['OS-EXT-SRV-ATTR:host']

    # 列号对应的排序属性
    col_map = {"0": "id",
               "1": "name",
               "2": "owner_id",
               "3": "size",
               "4": "host_name",
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
            query = Desktop.query
        else:
            query = Desktop.query.filter_by(owner_id=current_user.id)
    else:
        if (current_user.is_administrator()):
            query = Desktop.query.filter(or_(Desktop.name.like("%" + sSearch + "%"), Desktop.floating_ip.like("%" + sSearch + "%")))

            users = User.query.filter(User.username.like("%" + sSearch + "%"))
            for user in users:
                query_desktop = Desktop.query.filter_by(owner_id=user.id)
                query = query.union(query_desktop)
        else:
            query = Desktop.query.filter_by(owner_id=current_user.id).filter(or_(Desktop.name.like("%" + sSearch + "%"),
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
                "host_name":vm_host_dict.get(item.vm_ref,None),
                "ip":item.floating_ip,
                "status_chs":DesktopState.get_state_chs(item.desktop_state) if
                item.desktop_state else "创建中",
                "operation":{
                    "vmid" : item.vm_ref,
                    "name": item.name,
                    "status" : item.vm_state,
                    "size": flavorname,
                    "host_name": vm_host_dict.get(item.vm_ref,None),
                    "can_migrate_or_evacuate":item.can_migrate_or_evacuate()
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


@vmotion.route('/migrate_desktop', methods=['POST'])
@login_required
def migrate_desktop():
    migrate_desktop_form = MigrateDesktopForm()
    result = {}
    result['status'] = 'fail'
    result['error_info'] =""
    if migrate_desktop_form.validate_on_submit():
        try:
            desktop_vm_ref = migrate_desktop_form.desktop_vm_ref.data
            desktop_srchost = migrate_desktop_form.desktop_srchost.data
            desktop_desthost = migrate_desktop_form.desktop_desthost.data

            srchost = HostInfo.query.filter_by(
                host_name=desktop_srchost).first()
            if not srchost:
                result['status'] = 'fail'
                result['error_info'] = '桌面所在主机信息不存在'
                return jsonify(**result)
            desthost = HostInfo.query.filter_by(
                host_name=desktop_desthost).first()
            if not desthost:
                result['status'] = 'fail'
                result['error_info'] = '所选目标主机信息不存在'
                return jsonify(**result)
            if desthost.host_status != "up":
                result['status'] = 'fail'
                result['error_info'] = '所选目标主机状态异常，请刷新页面后重新选择目标主机'
                return jsonify(**result)

            if srchost.host_status == "up":
                if utils.migrate_desktop(desktop_vm_ref,desktop_desthost):
                    result['status'] = "success"
            elif srchost.external_network_state != "up" and \
                    srchost.management_network_state == "up" and \
                    srchost.service_state == "up":
                if utils.migrate_desktop(desktop_vm_ref,desktop_desthost):
                    result['status'] = "success"
            elif srchost.external_network_state != "up" and \
                    srchost.management_network_state == "up" and \
                    srchost.service_state != "up":
                result['status'] = 'fail'
                result['error_info'] = "桌面所在主机的计算服务异常，无法迁移"
            elif srchost.external_network_state == "up" and \
                    srchost.management_network_state != "up":
                result['status'] = 'fail'
                result['error_info'] = "桌面所在主机的管理网络异常，无法迁移"
            elif srchost.external_network_state == "up" and \
                    srchost.management_network_state == "up" and \
                    srchost.service_state != "up":
                result['status'] = 'fail'
                result['error_info'] = "桌面所在主机的计算服务异常，无法迁移"
            elif srchost.external_network_state != "up" and \
                    srchost.management_network_state != "up" and \
                            srchost.service_state == "up":
                result['status'] = 'fail'
                result['error_info'] = "桌面所在主机的访问网络及管理网络异常，无法迁移"
            elif srchost.external_network_state != "up" and \
                     srchost.management_network_state != "up" and srchost.service_state != "up":
                if utils.evacuate_desktop(desktop_vm_ref,desktop_desthost):
                    result['status'] = "success"
        except Exception as ex:
            print('ck', ex)
            LOG.error("Migrate Desktop Failed.")
            result['status'] = 'fail'
    return jsonify(**result)


@vmotion.route('/reset_desktop_status', methods=['POST'])
@login_required
def reset_desktop_status():
    #desktop_name = request.values.get("desktop_name")
    desktop_vm_ref = request.values.get("desktop_vm_ref")
    result = {}
    result["status"] = 'fail'
    result["error_info"] = ""
    try:
        desktop = Desktop.query.filter_by(vm_ref=desktop_vm_ref).first()
        if not desktop:
            result["status"] = 'fail'
            result["error_info"] = "该桌面不存在"
            return jsonify(**result)
        OpenstackComputeService.reset_server_state(desktop_vm_ref,"active")
        desktop.vm_state = "ACTIVE"
        desktop.desktop_state = "ACTIVE"
        db.session.add(desktop)
        db.session.commit()
        result['status'] = 'success'
    except:
        LOG.error("Reset Desktop Status Failed.")
        result['status'] = 'fail'

    return jsonify(**result)


@vmotion.route('/desktop_evacuation', methods=['GET'])
@login_required
def desktop_evacuation():
    pass


@vmotion.route('/migrate_task', methods=['GET'])
@login_required
def migrate_task():
    if not admin_permission.can():
        abort(403)

    """ Show all running task
    """
    return render_template('vmotion/migrate_task.html')


@vmotion.route('/task_table', methods=['GET'])
@login_required
def task_table():
    # 权限检查
    if not admin_permission.can():
        abort(403)

    """获取task_table指定页所需的task列表
    """
    # 列号对应的排序属性
    col_map = {"0": "id",
               "1": "updated_at",
               "2": "action",
               "3": "state",
               "4": "stage",
               "5": "retries",
               "6": "enabled",
               "7": "result",
               "8": "id",
               "9": "id"}

    sEcho = request.args.get('sEcho')
    iDisplayStart = request.args.get("iDisplayStart")
    iDisplayLength = request.args.get("iDisplayLength")
    sSearch = request.args.get("sSearch")
    iSortCol = request.args.get("iSortCol_0")
    sSortDir = request.args.get("sSortDir_0")
    if iSortCol is None:
        iSortCol = '1'
    if sSortDir is None:
        sSortDir = "desc"
    sort_col = col_map[iSortCol]

    query_tasklist = DesktopTask.query.filter(or_(DesktopTask.action.like("MIGRATE"),
                                         DesktopTask.action.like("EVACUATE")))

    if sSearch == '' or sSearch is None:
        query = query_tasklist
        # query = DesktopTask.query.order_by(DesktopTask.result_order, sort_col)    // 结果为ERROR的任务置顶
    else:
        query = query_tasklist.filter(or_(
            # DesktopTask.id.like("%"+sSearch+"%"),
            DesktopTask.action.like("%"+sSearch+"%"),
            DesktopTask.state.like("%"+sSearch+"%"),
            DesktopTask.stage.like("%"+sSearch+"%"),
            DesktopTask.retries.like("%"+sSearch+"%"),
            # DesktopTask.enabled.like("%"+sSearch+"%"),
            DesktopTask.result.like("%"+sSearch+"%")))
            # Course.query.filter_by(id=json.loads(DesktopTask.context).course_id).first().name.like("%"+sSearch+"%")))
        # query.order_by(DesktopTask.result_order, sort_col)    // 结果为ERROR的任务置顶

        courses = Course.query.filter(Course.name.like("%"+sSearch+"%")).all()
        for course in courses:
            query_task_for_course = query_tasklist.filter(or_(
                DesktopTask.context.like('%"course": '+str(course.id)+',%'),
                DesktopTask.context.like('%"course": '+str(course.id)+'}%')))
            query = query.union(query_task_for_course)

    sort_col = getattr(DesktopTask, sort_col)
    if sSortDir == "desc":
        query = query.order_by(sort_col.desc())
    else:
        query = query.order_by(sort_col.asc())

    page = int(iDisplayStart) // int(iDisplayLength)
    pagination = query.paginate(page+1, int(iDisplayLength), False)
    task_list = pagination.items
    task_json_list = []
    for item in task_list:
        task_json_list.append(
            {
                'id': item.id,
                'updated_at': datetime_format(item.updated_at),
                'idAndAction': {
                    'id':item.id,
                    'action':item.action
                },
                'state': TaskState.get_state_chs(item.state),
                'stage': item.stage,
                'retries':item.retries,
                'enabled':item.enabled,
                'result':item.result,
                'context':item.context,
                'id_enabled_result':{
                    'id':item.id,
                    'enabled':item.enabled,
                    'result':item.result
                }
            }
        )

    data = {"sEcho": sEcho,
            "iTotalRecords": str(pagination.total),
            "iTotalDisplayRecords": str(pagination.total),
            "aaData": task_json_list
            }
    db.session.remove()
    return jsonify(data)

@vmotion.route('/tasks/<int:id>', methods=['GET'])
@login_required
def task_detail(id):
    # 权限检查
    if not admin_permission.can():
        abort(403)

    """ Show task detail
    """
    task = DesktopTask.query.filter_by(id=id).first()
    if task is None:
        abort(404)
    stage_results = task.stage_results
    task_context_json = simplejson.loads(task.context)
    return render_template('vmotion/task_detail.html', stage_results=stage_results, task_context_json=task_context_json)


@vmotion.route('/tasks/', methods=['DELETE'])
@login_required
def delete_task():
    # 权限检查
    if not admin_permission.can():
        abort(403)

    result_json = {
        "status": "success",
        "data": {
            "success_list": [],
            "fail_list": []
        }
    }
    # 请求中包含所要删除的task_id列表
    tasks = request.json
    for id in tasks:
        task = DesktopTask.query.filter_by(id=int(id)).first()
        if task:
            stage_results = StageResult.query.filter_by(task_id = task.id).all()
            for stage_result in stage_results:
                db.session.delete(stage_result)
            db.session.delete(task)
            db.session.commit()
            ua_logger.info(current_user, "删除任务: %s" % task.id)
            result_json["data"]["success_list"].append(id)
        else:
            result_json["data"]["fail_list"].append(id)
    return jsonify(result_json)


@vmotion.route('/tasks/<string:action>', methods=['PUT'])
@login_required
def tasks_action(action):
    # 权限检查
    if not admin_permission.can():
        abort(403)

    result_json = {
        "status": "success",
        "data": {
            "success_list": [],
            "fail_list": []
        }
    }
    tasks = request.json
    for id in tasks:
        task = DesktopTask.query.filter_by(id=int(id)).first()
        if task:
            if action == "resume":
                desktop = simplejson.loads(task.context)["desktop"]
                vm_ref = Desktop.query.filter_by(id=desktop).first().vm_ref
                if OpenstackComputeService.get_server(vm_ref).status == "ERROR":
                    OpenstackComputeService.reset_server_state(vm_ref, "ACTIVE")
                # Continue the task from the fail stage
                task.resume()
                celery_tasks.run_migrationtask(task_id=task.id,
                                     link=celery_tasks._create_desktop_detect.s(
                                         task_id=task.id),
                                     link_error=celery_tasks._create_desktop_detect.s(
                                         task_id=task.id))
                ua_logger.info(current_user, "重做任务: %s" % task.id)
            elif action == "reset":
                desktop = simplejson.loads(task.context)["desktop"]
                vm_ref = Desktop.query.filter_by(id=desktop).first().vm_ref
                if OpenstackComputeService.get_server(vm_ref).status == "ERROR":
                    OpenstackComputeService.reset_server_state(vm_ref, "ACTIVE")
                # Reset the task to the initial state
                task.reset()
                celery_tasks.run_migrationtask(task_id=task.id,
                                     link=celery_tasks._create_desktop_detect.s(
                                         task_id=task.id),
                                     link_error=celery_tasks._create_desktop_detect.s(
                                         task_id=task.id))
                ua_logger.info(current_user, "重置任务: %s" % task.id)
            elif action == "disable":
                # Disable the task
                ua_logger.info(current_user, "禁用任务: %s" % task.id)
                task.disable()
            elif action == "enable":
                # Enable the task
                ua_logger.info(current_user, "启用任务: %s" % task.id)
                task.enable()
            result_json["data"]["success_list"].append(id)
        else:
            result_json["data"]["fail_list"].append(id)
    return jsonify(result_json)


@vmotion.route('/custom_migrate', methods=['POST'])
@login_required
def custom_migrate():
    result = {'status': 'fail', 'data': {}, 'error_info': ''}
    src_host = request.json.get("src_host")
    dest_hosts = request.json.get("dest_hosts")
    src_host_info = HostInfo.query.filter_by(host_name=src_host).first()
    dest_hosts_info = []
    if isinstance(dest_hosts, list):
        dest_hosts_info = HostInfo.query.filter(HostInfo.host_name.in_(dest_hosts)).all()
    if not dest_hosts_info:
        result['error_info'] = '所选目标主机信息不存在'
        return jsonify(**result)
    if not src_host_info:
        result['error_info'] = '桌面所在主机信息不存在'
        return jsonify(**result)
    for host_info in dest_hosts_info:
        if host_info.host_status != "up":
            result['error_info'] = '所选目标主机状态异常，请刷新页面后重新选择目标主机'
            return jsonify(**result)
    NO_OPERATION, MIGRATE, EVACUATE = 0, 1, 2
    method = NO_OPERATION
    if src_host_info.host_status == "up":
        method = MIGRATE
    elif src_host_info.external_network_state != "up" and \
                    src_host_info.management_network_state == "up" and \
                    src_host_info.service_state == "up":
        method = MIGRATE
    elif src_host_info.external_network_state != "up" and \
                    src_host_info.management_network_state == "up" and \
                    src_host_info.service_state != "up":
        result['error_info'] = "桌面所在主机的计算服务异常，无法迁移"
    elif src_host_info.external_network_state == "up" and \
                    src_host_info.management_network_state != "up":
        result['error_info'] = "桌面所在主机的管理网络异常，无法迁移"
    elif src_host_info.external_network_state == "up" and \
                    src_host_info.management_network_state == "up" and \
                    src_host_info.service_state != "up":
        result['error_info'] = "桌面所在主机的计算服务异常，无法迁移"
    elif src_host_info.external_network_state != "up" and \
                    src_host_info.management_network_state != "up" and \
                    src_host_info.service_state == "up":
        result['error_info'] = "桌面所在主机的访问网络及管理网络异常，无法迁移"
    elif (src_host_info.external_network_state != "up" and
                  src_host_info.management_network_state != "up" and
                  src_host_info.service_state != "up"):
        method = EVACUATE
    if method == NO_OPERATION:
        return jsonify(**result)
    try:
        # Put dest host info into a heap
        dest_hosts_heap = []
        for host_info in dest_hosts_info:
            # print(host_info.mem_used, type(host_info.mem_used))
            # !! type(host_info.mem_used) is str?
            heapq.heappush(dest_hosts_heap,
                           (int(host_info.mem_used)-int(host_info.mem),
                            host_info.host_name))
        search_opts = {'host': src_host}
        vm_list = OpenstackComputeService.list_servers(search_opts=search_opts)
        success_count, fail_count = 0, 0
        if method == MIGRATE:
            migrate = utils.migrate_desktop
        elif method == EVACUATE:
            migrate = utils.evacuate_desktop
        for vm in vm_list:
            if vm.status == 'ACTIVE':
                # 没有检查目标内存是否足够
                vm_ram = OpenstackComputeService.get_flavor(vm.flavor['id']).ram
                top_item = heapq.heappop(dest_hosts_heap)
                target_host = (top_item[0]+vm_ram, top_item[1])
                heapq.heappush(dest_hosts_heap, target_host)
                if migrate(vm.id, target_host[1]):
                    success_count += 1
                else:
                    fail_count += 1
        result['status'] = 'success'
        result['data'] = '创建迁移任务 %d个成功 %d个失败' % (success_count, fail_count)
    except Exception as e:
        LOG.error("Migrate Desktop Failed.")
        result['status'] = 'fail'

    return jsonify(result)

@vmotion.route('/batch_migrate', methods=['POST'])
@login_required
def batch_migrate():
    result = {'status': 'fail', 'data': {}, 'error_info': ''}
    vm_list = request.json.get("vm_list")
    dest_hosts = request.json.get("dest_hosts")
    # Check whether vm_id is valid
    all_vms = OpenstackComputeService.list_servers()
    vm_dict = dict([(vm.id, vm) for vm in all_vms])
    checked_vms = {}
    src_host_names = []
    src_host_info_dict = {}
    for vm_id in vm_list:
        if vm_id in vm_dict:
            checked_vms[vm_id] = vm_dict[vm_id]
            checked_vms[vm_id].host_name = checked_vms[vm_id].\
                to_dict()['OS-EXT-SRV-ATTR:host']
            src_host_names.append(checked_vms[vm_id].host_name)
    if not checked_vms:
        result['error_info'] = '没有有效的桌面'
        return jsonify(result)
    src_host_infos = HostInfo.query.\
        filter(HostInfo.host_name.in_(src_host_names)).all()
    for host_info in src_host_infos:
        src_host_info_dict[host_info.host_name] = host_info
    print('ddd')
    print(src_host_info_dict)
    # Check dest host
    dest_hosts_info = []
    if isinstance(dest_hosts, list):
        dest_hosts_info = HostInfo.query.\
            filter(HostInfo.host_name.in_(dest_hosts)).all()
    if not dest_hosts_info:
        result['error_info'] = '所选目标主机信息不存在'
        return jsonify(result)
    for host_info in dest_hosts_info:
        if host_info.host_status != "up":
            result['error_info'] = '所选目标主机状态异常，请刷新页面后重新选择目标主机'
            return jsonify(**result)
    # Put dest host info into a heap
    dest_hosts_heap = []
    for host_info in dest_hosts_info:
        heapq.heappush(dest_hosts_heap,
                       (int(host_info.mem_used) - int(host_info.mem),
                        host_info.host_name))
    # Check the staus of hosts which holds vms and select suitable operation.
    for vm_id, vm in checked_vms.items():
        if vm.status != 'ACTIVE':
            continue
        vm_ram = OpenstackComputeService.get_flavor(vm.flavor['id']).ram
        top_item = heapq.heappop(dest_hosts_heap)
        target_host = (top_item[0] + vm_ram, top_item[1])
        heapq.heappush(dest_hosts_heap, target_host)
        host_info = src_host_info_dict[vm.host_name]
        if host_info.host_status == "up":
            if utils.migrate_desktop(vm_id, target_host[1]):
                result['status'] = "success"
        elif host_info.external_network_state != "up" and \
                        host_info.management_network_state == "up" and \
                        host_info.service_state == "up":
            if utils.migrate_desktop(vm_id, target_host[1]):
                result['status'] = "success"
        elif host_info.external_network_state != "up" and \
                        host_info.management_network_state == "up" and \
                        host_info.service_state != "up":
            result['status'] = 'fail'
            result['error_info'] = "桌面所在主机的计算服务异常，无法迁移"
        elif host_info.external_network_state == "up" and \
                        host_info.management_network_state != "up":
            result['status'] = 'fail'
            result['error_info'] = "桌面所在主机的管理网络异常，无法迁移"
        elif host_info.external_network_state == "up" and \
                        host_info.management_network_state == "up" and \
                        host_info.service_state != "up":
            result['status'] = 'fail'
            result['error_info'] = "桌面所在主机的计算服务异常，无法迁移"
        elif host_info.external_network_state != "up" and \
                        host_info.management_network_state != "up" and \
                        host_info.service_state == "up":
            result['status'] = 'fail'
            result['error_info'] = "桌面所在主机的访问网络及管理网络异常，无法迁移"
        elif host_info.external_network_state != "up" and \
                        host_info.management_network_state != "up" and host_info.service_state != "up":
            if utils.evacuate_desktop(vm_id, target_host[1]):
                result['status'] = "success"
    return jsonify(result)

@vmotion.route('/batch_reset_desktop_status', methods=['POST'])
@login_required
def batch_reset_desktop_status():
    result = {'status': 'fail', 'data': {}, 'error_info': ''}
    vm_list = request.json.get("vm_list")

    if not isinstance(vm_list, list) or not vm_list:
        result["error_info"] = "提供的桌面列表无效"
        return jsonify(**result)
    valid_count, invalid_count = 0, 0
    try:
        for vm_id in vm_list:
            desktop = Desktop.query.filter_by(vm_ref=vm_id).first()
            if not desktop:
                invalid_count += 1
            else:
                valid_count += 1
                OpenstackComputeService.reset_server_state(vm_id, "active")
                desktop.vm_state = "ACTIVE"
                desktop.desktop_state = "ACTIVE"
                db.session.add(desktop)
        db.session.commit()
        result['data'] = '共重置 %d个桌面， 忽略 %d个无效桌面' % (valid_count,
                                                    invalid_count)
        result['status'] = 'success'
    except:
        LOG.error("Reset Desktop Status Failed.")
        result['status'] = 'fail'

    return jsonify(**result)