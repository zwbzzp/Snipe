# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# comment
#
# 2016/3/17 lipeizhao : Init

import datetime

from flask import render_template, request, jsonify, flash, redirect, url_for
from flask.ext.login import login_required, current_user
from flask import send_from_directory,send_file
from . import setting
from .utils import ParamsValidator, is_timetable_legal, check_time_conflict, \
    judge_file

from ..models import Parameter, Period, Flavor, Course, Image, \
    Protocol, License,TerminalState, Policy

from .. import db, csrf
from ..common import timeutils, imageutils
import logging

import os

from phoenix.cloud import compute as OpenstackComputeService
from .forms import FlavorForm, FlavorEditForm, ParamForm, CourseTimeForm, PolicyForm
from phoenix.cloud import image as OpenstackImageService
from ..license.utils import LicenseUtils
from ..log.utils import UserActionLogger

LOG = logging.getLogger(__name__)
ua_logger = UserActionLogger()



def parameter_extract_by_group(parameters):
    parameter_group = {}
    #groups = ParamGroup.query.all()
    for parameter in parameters:
        if parameter.group == "" or parameter.group == None:
            if "system" not in parameter_group:
                parameter_group["system"] = {}
            parameter_group["system"][parameter.name] = {
                "description": parameter.description, "name": parameter.name,
                "value": parameter.value}
        else:
            if parameter.group not in parameter_group:
                parameter_group[parameter.group]={}
            parameter_group[parameter.group][parameter.name] = {
                "description": parameter.description, "name": parameter.name,
                "value": parameter.value}
    return parameter_group

@setting.route('/parameters', methods=['GET'])
@login_required
def parameters():
    parameters = Parameter.query.all()
    parameter_group = parameter_extract_by_group(parameters)

    flavor_list = OpenstackComputeService.list_flavors()
    flavors = []
    flavor_name_dict = {}
    for flavor in flavor_list:
        flavors.append({'id': flavor.id, 'name':flavor.name})
        flavor_name_dict[flavor.id]=flavor.name

    image_list = imageutils.list_of_image()
    images = []
    image_name_dict = {}
    for image in image_list:
        images.append({'id': image.id, 'name': image.name})
        image_name_dict[image.id] = image.name
    protocols = Protocol.query.all()
    policies = Policy.query.all()
    return render_template('setting/parameters.html', parameters=parameters,
                           parameter_group=parameter_group,
                           flavors=flavors, flavor_name_dict=flavor_name_dict,
                           images=images, image_name_dict=image_name_dict,
                           protocols=protocols,policies=policies,TerminalState=TerminalState)


@setting.route('/parameters/batch_update', methods=['POST'])
@login_required
def batch_update_parameters():
    parameters = request.json
    result = {'result': 'success',
              'parameters': None}
    try:
        for p in parameters:
            param = Parameter.query.filter_by(name=p).first()
            param.value = parameters[p]
            db.session.add(param)
            db.session.add(param)
            ua_logger.info(current_user, "更新系统参数: %s" % p)
            LOG.info("update system parameter: %s" % p)
        db.session.commit()
        newparameters = Parameter.query.all()
        result['result'] = 'success'

    except Exception as e:
        result['result'] = 'fail'
        LOG.exception("update system parameter fail")

    return jsonify(**result)


@setting.route('/timetable', methods=['GET'])
@login_required
def timetable():
    timetable_list = Period.query.order_by(db.asc(Period.start_time)).all()
    form = CourseTimeForm()
    return render_template('setting/timetable.html',
                           timetable_list=timetable_list, form=form)


@setting.route('/timetable/add', methods=['POST'])
@login_required
def add_period():
    form = CourseTimeForm()
    if form.validate_on_submit():
        start_time = form.start_time.data.time()
        end_time = form.end_time.data.time()
        if start_time >= end_time:
            flash(u"添加失败，开始时间必须小于结束时间", category="error")
            LOG.debug("添加失败，开始时间必须小于结束时间")
        else:
            periods = Period.query.all()
            if not check_time_conflict(start_time, end_time, periods):
                flash(u"添加失败，课时时间与原有课时冲突", category="error")
                LOG.warning("添加时间段失败，课时时间与原有课时冲突")
            else:
                period = Period(start_time=start_time, end_time=end_time)
                db.session.add(period)
                Period.refresh_names()
                db.session.commit()
                ua_logger.info(current_user, "成功添加时段: %s-%s" % (start_time, end_time))
                LOG.info("成功添加时段: %s-%s" % (start_time, end_time))
                flash(u"添加课时成功", category="info")
    else:
        flash(u"添加失败，课时时间不合法", category="error")
        LOG.debug("添加失败，课时时间不合法")
    return redirect(url_for('setting.timetable'))


@setting.route('/timetable/update', methods=['POST'])
@login_required
def update_timetable():
    timetable = request.json
    result = {"result": ""}
    if is_timetable_legal(timetable):
        try:
            periods = Period.query.all()
            for period in periods:
                new_p = timetable[str(period.id)]
                new_start_time = timeutils.str_to_time(new_p['start_time'])
                new_end_time = timeutils.str_to_time(new_p['end_time'])
                if period.start_time != new_start_time or period.end_time != new_end_time:
                    period.start_time = new_start_time
                    period.end_time = new_end_time
                    db.session.add(period)
                    period.update_lessons()
                    ua_logger.info(current_user, "成功更新时段: %s-%s" % (period.start_time, period.end_time))
            Period.refresh_names()
            db.session.commit()
            flash(u"添加失败，课时时间不合法", category="info")
            LOG.info("添加失败，课时时间不合法")
            result = {"result": "success"}
        except:
            LOG.exception('Failed to update timetable')
            result = {"result": "fail"}
            flash(u"更新时间表失败", category="error")
    else:
        result = {"result": "fail"}
        flash(u"更新时间表失败", category="error")
        LOG.debug("更新时间表设置不合法")
    return jsonify(**result)


@setting.route('/timetable/reset', methods=['POST'])
@login_required
def reset_timetable():
    timeTable = request.json
    result = {"result": ""}
    timelist = Period.query.all()
    if timelist:
        result = {"result": "fail"}
        return jsonify(**result)
    if is_timetable_legal(timeTable):
        try:
            for newtime in timeTable:
                new_period = Period()
                new_period.id = newtime
                new_period.name = newtime
                value = timeTable[newtime]
                new_period.start_time = timeutils.time_format(value["start_time"])
                new_period.end_time = timeutils.time_format(value["end_time"])
                db.session.add(new_period)
            db.session.commit()
            flash(u"重置课时成功", category="info")
            ua_logger.info(current_user, "重置课时成功!")
            LOG.info("Reset timetable successfully")
            result = {"result": "success"}
        except:
            result = {"result": "fail"}
            LOG.exception("Reset timetable fail")
    else:
        result = {"result": "fail"}
    return jsonify(**result)


@setting.route('/timetable/delete', methods=['POST'])
@login_required
def delete_period():
    period_ids = request.json
    result = {"result": ""}
    for period_id in period_ids:
        period = Period.query.filter_by(id=period_id).first()
        period.delete_lessons()
        db.session.delete(period)
        ua_logger.info(current_user, "成功删除时段: %s-%s" % (period.start_time, period.end_time))
        LOG.info("成功删除时段: %s-%s" % (period.start_time, period.end_time))
    Period.refresh_names()
    try:
        db.session.commit()
        result = {"result": "success"}
        flash(u"删除课时成功", category="info")
    except:
        LOG.exception("Delete period fail")
        result = {"result": "fail"}
    return jsonify(**result)


def check_flavor_using(flavor_id):
    course_list = Course.query.filter_by(flavor_ref=flavor_id).all()
    if course_list:
        return True
    else:
        return False


@setting.route('/flavor', methods=['GET'])
@login_required
def flavor():
    try:
        flavor_list = OpenstackComputeService.list_flavors()
        using_flavor = []
        for flavor in flavor_list:
            if check_flavor_using(flavor.id):
                using_flavor.append(flavor.id)
        return render_template('setting/flavor.html',
                               flavor_list=flavor_list,
                               using_flavor=using_flavor)
    except Exception as e:
        LOG.exception("Get flavor list fail")
        return render_template('setting/flavor.html')


@setting.route('/add_flavor', methods=['POST'])
@login_required
def add_flavor():
    flavor_form = FlavorForm()
    result = {}
    result['status'] = "fail"
    if flavor_form.validate_on_submit():
        try:
            new_flavor = OpenstackComputeService.create_flavor(
                flavor_form.name.data, flavor_form.ramnum.data,
                flavor_form.cpunum.data, flavor_form.disknum.data)

            if new_flavor.id:
                flavor = Flavor()
                flavor.ref_id = new_flavor.id
                flavor.name = new_flavor.name
                flavor.description =  "%dCPU | %dM RAM | %dG Disk" % (new_flavor.vcpus, new_flavor.ram, new_flavor.disk)
                db.session.add(flavor)
                db.session.commit()
                LOG.info("Add New Flavor(ID: %s, Name: %s) Sucessfully"
                         % (str(new_flavor.id), flavor_form.name.data))
                ua_logger.info(current_user, "成功创建配置: %s" % new_flavor.id)
                result['status'] = "success"
            else:
                LOG.info("Add New Flavor Failed.")
                result['status'] = "fail"
        except Exception as e:
            if e.message.find("exists"):
                result['status'] = "existed"
                result['name'] = flavor_form.name.data
            else:
                result['status'] = "fail"
            LOG.exception("Add New Flavor Failed")
    return jsonify(**result)


@setting.route('/update_flavor', methods=['POST'])
@login_required
def update_flavor():
    flavor_edit_form = FlavorEditForm()
    result = {}
    if flavor_edit_form.validate_on_submit():
        try:
            old_flavor = OpenstackComputeService.get_flavor(
                flavor_edit_form.flavorid.data)
            flavor_list = OpenstackComputeService.list_flavors()
            for flavor in flavor_list:
                if flavor.name == flavor_edit_form.name.data \
                        and flavor_edit_form.flavorid.data != flavor.id:
                    result['status'] = "existed"
                    result['name'] = flavor_edit_form.name.data
                    return jsonify(**result)

            try:
                OpenstackComputeService.delete_flavor(
                    flavor_edit_form.flavorid.data)
                old_flavor_item = Flavor.query.filter_by(
                    ref_id=flavor_edit_form.flavorid.data).first()
                if old_flavor_item:
                    db.session.delete(old_flavor_item)
                    db.session.commit()


                new_flavor = OpenstackComputeService.create_flavor(
                    flavor_edit_form.name.data, flavor_edit_form.ramnum.data,
                    flavor_edit_form.cpunum.data, flavor_edit_form.disknum.data)

                flavor = Flavor()
                flavor.ref_id = new_flavor.id
                flavor.name = new_flavor.name
                flavor.description = "%dCPU | %dM RAM | %dG Disk" % (new_flavor.vcpus, new_flavor.ram, new_flavor.disk)
                db.session.add(flavor)
                db.session.commit()

                #To Do: Update Course Flavor Ref
                from ..models import Course
                course_list = Course.query.filter_by(flavor_ref=flavor_edit_form.flavorid.data).all()
                for course in course_list:
                    course.flavor_ref = new_flavor.id
                    db.session.add(course)
                    db.session.commit()
                LOG.info("Update  Flavor: Old ID: %s New ID: %s" % (old_flavor.id, new_flavor.id))
                ua_logger.info(current_user, "成功更新配置: %s" % new_flavor.id)
                result['status'] = 'success'
            except Exception as e:
                LOG.exception("Update Flavor Failed")
                result['status'] = 'fail'
        except Exception as ex:
            LOG.exception("Get Flavor Failed")
            result['status'] = 'fail'
        return jsonify(**result)
    return jsonify(**result)


@setting.route('/delete_flavor', methods=['POST'])
@login_required
def delete_flavor():
    result = {}
    ids = request.values.getlist('ids[]')
    try:
        for fid in ids:
            OpenstackComputeService.delete_flavor(fid)
            flavor = Flavor.query.filter_by(ref_id=fid).first()
            if flavor:
                db.session.delete(flavor)
                db.session.commit()
            LOG.info("Delete Flavor ID: %s" % fid)
            ua_logger.info(current_user, "成功删除配置: %s" % fid)
        result['status'] = "success"
    except Exception as e:
        LOG.exception("Delete Flavors Error")
        result['status'] = "fail"
    return jsonify(**result)


@setting.route('/free_desktop_params', methods=['POST'])
def free_desktop_params():
    ret = {"status": "", "reason": ""}
    free_desktop_param_form = ParamForm()
    if free_desktop_param_form.validate_on_submit():
        try:
            # update these datas to db
            update_params = {"free_desktop_start_time": None,
                             "free_desktop_stop_time": None,
                             "free_desktop_switch": None,
                             "free_desktop_capacity": None,
                             "free_desktop_flavor": None,
                             "free_desktop_image": None}
            # the start and stop time in the form is datetime, we just need the %H:%M
            free_desktop_start_time = free_desktop_param_form.free_desktop_start_time.data
            update_params["free_desktop_start_time"] = "%02d:%02d" % (
                free_desktop_start_time.hour, free_desktop_start_time.minute)
            free_desktop_stop_time = free_desktop_param_form.free_desktop_stop_time.data
            update_params["free_desktop_stop_time"] = "%02d:%02d" % (
                free_desktop_stop_time.hour, free_desktop_stop_time.minute)

            update_params[
                "free_desktop_switch"] = free_desktop_param_form.free_desktop_switch.data
            update_params[
                "free_desktop_capacity"] = free_desktop_param_form.free_desktop_capacity.data
            update_params[
                "free_desktop_flavor"] = free_desktop_param_form.free_desktop_flavor.data
            update_params[
                "free_desktop_image"] = free_desktop_param_form.free_desktop_image.data

            for param, value in update_params.items():
                param_obj = Parameter.query.filter_by(name=param).first()
                param_obj.value = value
                db.session.add(param_obj)
            db.session.commit()

            ret["status"] = "success"
        except Exception as ex:
            import traceback
            traceback.print_exc()
            LOG.exception("Get free desktop params fail")
            ret["status"] = "fail"
            ret["reason"] = str(ex)
    else:
        ret["status"] = "fail"
        ret["reason"] = "form data is not valid"
    print(ret)
    return jsonify(ret)


@setting.route('/get_flavor', methods=['GET', 'POST'])
def get_flavor():
    ret = {"status": "", "min_ram": 0, "min_disk": 0, "reason": ""}
    try:
        image_id = request.form["image_id"]
        image = OpenstackImageService.get_image(image_id)
        ret["min_ram"] = image.get("min_ram", 0)
        ret["min_disk"] = image.get("min_disk", 0)
        ret["status"] = "success"
    except Exception as ex:
        ret["status"] = "fail"
        ret["reason"] = str(ex)
        LOG.exception("Fail to get flavor")
    print(ret)
    return jsonify(ret)

@setting.route('/flavor_adaptor', methods=['GET', 'POST'])
def flavor_adaptor():
    ret = {"status" : "", "min_ram": 0, "min_disk": 0, "reason": ""}
    try:
        flavor_id = request.form.get("flavorid", None)
        if not flavor_id:
            ret["status"] = "fail"
            ret["reason"] = "flavor id cannot be empty"
        else:
            # the flovor's ram and disk must satisfy all the courses's images
            # so the flavor's min ram must not less than the max ram of the images, the min disk is the same
            max_ram = max_disk = 0

            # get all the courses which use this flavor
            course_list = Course.query.filter_by(flavor_ref=flavor_id).all()
            for course in course_list:
                image_ref = course.image_ref
                if image_ref:
                    try:
                        image = OpenstackImageService.get_image(image_ref)
                        image_min_ram = image.get("min_ram", 0)
                        image_min_disk = image.get("min_disk", 0)
                        if image_min_ram > max_ram:
                            max_ram = image_min_ram
                        if image_min_disk > max_disk:
                            max_disk = image_min_disk
                    except Exception as ex:
                        # FIXME: when the image not found, it will throw glanceclient.exc.HTTPNotFound
                        LOG.exception(ex)
            ret["status"] = "success"
            ret["min_ram"] = max_ram
            ret["min_disk"] = max_disk
    except Exception as ex:
        LOG.exception(ex)
        ret["status"] = "fail"
        ret["reason"] = str(ex)

    return jsonify(ret)

@setting.route('/about', methods=['GET'])
def about():
    license_info = License.query.all()
    if license_info is None or len(license_info) == 0:
        license_info ={"max_desktops": 0,
                       "max_user": 1,
                       "max_images": 0,
                       "max_vcpu": 0,
                       "max_vmem": 0,
                       "max_vdisk": 0,
                       "expired_time":datetime.datetime.now()}
    else:
        license_info = license_info[0]
    now = datetime.datetime.now()
    return render_template('setting/about.html', license_info=license_info,
                           now=now)


@setting.route('/host_info_file', methods=['GET'])
def host_info_file():
    basedir = os.path.abspath(os.path.dirname(__file__))
    basedir = os.path.join(basedir, '../static/')
    host_info_file_path = os.path.join(basedir, 'hostinfo.dat')
    if not os.path.exists(host_info_file_path):
        system_license_info = License.query.all()
        license_utils = LicenseUtils()
        if system_license_info is None or len(system_license_info) == 0 or \
                system_license_info[0].system_serial_number == None or \
                system_license_info[0].system_serial_number == "" :
            flash('请填写并保存管理系统序列号后再下载生成主机信息', 'info')
            LOG.debug('请填写并保存管理系统序列号后再下载生成主机信息')
            return redirect((url_for('setting.about')))
        else:
            (status,mac,sn) = license_utils.generate_host_info(
                system_license_info[0].system_serial_number)
            system_license_info = system_license_info[0]
            system_license_info.server_serial_number = sn
            system_license_info.mac_address = mac
        db.session.add(system_license_info)
        db.session.commit()
        LOG.info("下载生成主机信息")
    return send_file('static/hostinfo.dat')


@setting.route('/upload_license_file', methods=['POST'])
@login_required
def upload_license_file():
    result = {"status": "fail", "error_msg": ""}
    try:
        upload_file = request.files.get("file")
        if upload_file is None:
            result["error_msg"] = "许可文件不能为空"
            return jsonify(**result)


        # the size of upload file cannot bigger than 1MB
        if upload_file.content_length > 1 * 1024 * 1024:
            result["error_msg"] = "许可文件大小不能超过1MB"
            return jsonify(**result)

        license_utils = LicenseUtils()
        (max_desktops, max_user, max_images, max_vcpu, max_vmem, max_vdisk, expired_time,mac,sn) = license_utils.get_license_info_from_upload_file(upload_file)

        if mac != license_utils.get_mac_address() or sn != \
                license_utils.get_serial_number():
            result['error_msg'] = "许可文件与硬件信息不匹配!"
            result["status"] = "fail"
            return jsonify(**result)

        system_license_info = License.query.all()
        if system_license_info is None or len(system_license_info) == 0:
            system_license_info = License()
            system_license_info.max_desktops = int(max_desktops)
            system_license_info.max_images = int(max_images)
            system_license_info.max_user = int(max_user)
            system_license_info.max_vcpu = int(max_vcpu)
            system_license_info.max_vmem = int(max_vmem)
            system_license_info.max_vdisk = int(max_vdisk)
            system_license_info.expired_time = datetime.datetime.strptime(
                expired_time,
                "%Y-%m-%d")
            db.session.add(system_license_info)
            db.session.commit()
        elif system_license_info[0].system_serial_number == None or \
                        system_license_info[0].system_serial_number == "":
            result['error_msg'] ="请填写并保存管理系统序列号后再上传许可文件!"
            result["status"] = "fail"
        else:
            system_license_info[0].max_desktops = int(max_desktops)
            system_license_info[0].max_images = int(max_images)
            system_license_info[0].max_user = int(max_user)
            system_license_info[0].max_vcpu = int(max_vcpu)
            system_license_info[0].max_vmem = int(max_vmem)
            system_license_info[0].max_vdisk = int(max_vdisk)
            system_license_info[0].expired_time = datetime.datetime.strptime(expired_time,
                                                                          "%Y-%m-%d")
            db.session.add(system_license_info[0])
            db.session.commit()
            result["status"] = "success"
            ua_logger.info(current_user, "成功上传许可文件!")
            LOG.info("成功上传许可文件!")
    except Exception as ex:
        LOG.exception("Upload License File Failed: %s", ex)
        result['error_msg'] = "请确保上传正确的许可文件!"
        result["status"] = "fail"
    return jsonify(**result)


@setting.route('/license/batch_update', methods=['POST'])
@login_required
def batch_update_license():
    license_info = request.json
    result = {'status': 'success'}
    try:
        lice = License.query.first()
        if not lice:
            lice = License()
        for l in license_info:
            if l == 'license_system_serial_number':
                lice.system_serial_number = license_info[l]
            else:
                if license_info[l].endswith('/'):
                    license_info[l] = license_info[l][:-1]
                lice.server_url = license_info[l]
            db.session.add(lice)
        db.session.commit()
        ua_logger.info(current_user, "成功更新许可信息!")
        LOG.info("成功更新许可信息!")
        result['status'] = 'success'
    except Exception as e:
        LOG.exception('batch update license fail: %s', e)
        result['status'] = 'error'
    return jsonify(**result)


@setting.route('/invoke_system')
@login_required
def invoke_system():
    result = {"status": "fail", "error_msg": ""}
    try:
        license_info = License.query.first()
        if license_info == None or license_info.system_serial_number == "" or\
                license_info.server_url == "":
            result['error_msg'] = "请填写并保存管理系统序列号或许可证服务器url后再激活管理系统!"
            result['status'] = "fail"
            return jsonify(**result)
        license_utils = LicenseUtils()
        (status,mac,sn) = license_utils.generate_host_info(
            license_info.system_serial_number)
        if status == 'No Vinzor Public Key':
            result['error_msg'] = "请联系广州云晫信息有限公司获取许可系统公钥!"
            result['status'] = "fail"
            return jsonify(**result)
        upload_result = license_utils.upload_hostinfo(license_info.server_url,
                                      license_info.system_serial_number)
        if upload_result != True:
            result['error_msg'] = "激活失败：无法上传主机信息!"
            result['status'] = "fail"
            return jsonify(**result)
        download_result = license_utils.download_license_file(
            license_info.server_url, license_info.system_serial_number)
        if download_result != True:
            result['error_msg'] = "激活失败：无法下载许可文件!"
            result['status'] = "fail"
            return jsonify(**result)
        (max_desktops, max_user, max_images, max_vcpu, max_vmem, max_vdisk, expired_time,mac,sn) = license_utils.get_license_info()
        if status == "success":
            license_info.server_serial_number = sn
            license_info.mac_address = mac
        license_info.max_desktops = int(max_desktops)
        license_info.max_images = int(max_images)
        license_info.max_user = int(max_user)
        license_info.max_vcpu = int(max_vcpu)
        license_info.max_vmem = int(max_vmem)
        license_info.max_vdisk = int(max_vdisk)
        license_info.expired_time = datetime.datetime.strptime(
            expired_time,
            "%Y-%m-%d")
        db.session.add(license_info)
        db.session.commit()
        ua_logger.info(current_user, "成功激活管理系统!")
        result['status'] = "success"
    except Exception as ex:
        LOG.exception("激活操作失败")
        result['status'] = "fail"
    return jsonify(**result)



@setting.route('/system_policy', methods=['GET'])
@login_required
def system_policy():
    policy_list = Policy.query.all()
    form = PolicyForm()
    edit_form = PolicyForm()
    return render_template('setting/system_policy.html', policy_list=policy_list, form=form, edit_form=edit_form)

@setting.route('/system_policy', methods=['POST'])
@login_required
def add_system_policy():
    result = {'result': 'success'}
    policy_form = PolicyForm()
    if policy_form.validate_on_submit():
        existed_policy = Policy.query.filter_by(name=policy_form.name.data).first()
        if existed_policy:
            result['result'] = 'existed'
            result['name'] = existed_policy.name
            flash("外设策略 {0} 已存在，策略添加失败".format(existed_policy.name), 'error')
        else:
            policy = Policy()
            policy.name = policy_form.name.data
            policy.enable_usb = policy_form.enable_usb.data
            policy.enable_clipboard = policy_form.enable_clipboard.data
            policy.enable_audio = policy_form.enable_audio.data
            db.session.add(policy)
            db.session.commit()
            ua_logger.info(current_user, "添加外设策略：%s" % policy_form.name.data)
            result['result'] = 'success'
            flash("外设策略 {0} 添加成功".format(policy_form.name.data), 'info')
    else:
        result['result'] = 'fail'
        flash("提交信息不合法,添加失败", 'error')
    return redirect(url_for("setting.system_policy"))

@setting.route('/update_system_policy/<int:id>', methods=['POST'])
@login_required
def update_policy(id):
    result = {'result': 'success'}
    policy_form = PolicyForm()
    if policy_form.validate_on_submit():
        policy = Policy.query.filter_by(id=id).first()
        if policy is not None:
            if policy.name == policy_form.name.data:
                policy.name = policy_form.name.data
                policy.enable_usb = policy_form.enable_usb.data
                policy.enable_clipboard = policy_form.enable_clipboard.data
                policy.enable_audio = policy_form.enable_audio.data
                db.session.add(policy)
                db.session.commit()
                ua_logger.info(current_user, "修改外设策略：%s" % policy_form.name.data)
                result['result'] = 'success'
                flash("外设策略 {0} 修改成功".format(policy_form.name.data), 'info')
            else:
                exist_policy = Policy.query.filter_by(name=policy_form.name.data).all()
                if len(exist_policy) > 0:
                    result['result'] = 'name-existed'
                    result['name'] = policy_form.name.data
                    flash("策略名称不可重复，外设策略 {0} 修改失败".format(policy.name), 'error')
                else:
                    policy.name = policy_form.name.data
                    policy.enable_usb = policy_form.enable_usb.data
                    policy.enable_clipboard = policy_form.enable_clipboard.data
                    policy.enable_audio = policy_form.enable_audio.data
                    db.session.add(policy)
                    db.session.commit()
                    ua_logger.info(current_user, "修改外设策略：%s" % policy_form.name.data)
                    result['result'] = 'success'
                    flash("外设策略 {0} 修改成功".format(policy_form.name.data), 'info')
        else:
            result['result'] = 'not-existed'
            result['name'] = policy_form.name.data
            flash("外设策略 {0} 不存在存在,策略修改失败".format(policy_form.name.data), 'error')
    else:
        result['result'] = 'fail'
        flash("提交信息不合法,修改失败", 'error')
    return redirect(url_for("setting.system_policy"))

@setting.route('/delete_policy', methods=['DELETE'])
@login_required
def delete_policies():
    policies = request.json
    success_count = 0
    fail_count = 0
    result ={
        'result': 'success'
    }
    for policy_id in policies:
        policy = Policy.query.filter_by(id=policy_id).first()
        if policy is not None:
            if policy.courses.count() > 0:
                fail_count = fail_count + 1
                LOG.error("Unable to delete policy %s, has been using by %s courses" % (policy.id, policy.courses.count()))
            else:
                success_count = success_count + 1
                flash("外设策略 {0} 删除成功".format(policy.name), 'info')
                LOG.info("Delete policy %s" % (policy.name))
                db.session.delete(policy)
        else:
            fail_count = fail_count + 1
            LOG.warn("Policy %s is not exist" % (policy.name))
    db.session.commit()
    flash(
        '尝试添加{0}个外设策略,其中成功{1}个,失败{2}个'.format(
            success_count + fail_count,
            success_count,
            fail_count),
        'info'
    )
    if fail_count == 0:
        result['result'] = 'success'
    else:
        result['result'] = 'error'
    return jsonify(result)



