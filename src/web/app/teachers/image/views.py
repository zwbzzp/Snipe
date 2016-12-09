# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# comment
#
# 2016/3/31 qinjinghui : Init
__author__ = 'qinjinghui'


import datetime
import iso8601
from flask import render_template, request, jsonify
from flask.ext.login import login_required, current_user
from . import image

from ... import db, csrf
from ...common import timeutils
import logging
import time
import simplejson
from threading import Thread

from phoenix.cloud import image as OpenstackImageService
from phoenix.cloud import compute as OpenstackComputeService
from phoenix.cloud import network as OpenstackNetworkService
from .forms import ImageEditForm, LaunchInstanceForm
from ...models import Image, Course, Desktop, User, Permission,DesktopType,\
    DesktopState,Flavor
from . import utils
from ...auth.principal import admin_permission
from phoenix.common import timeutils
from ..log.utils import UserActionLogger
from ...common import imageutils

LOG = logging.getLogger(__name__)
ua_logger = UserActionLogger()

@login_required
def check_img_using(image_id):
    """return true if using else false"""
    course_list = Course.query.filter_by(image_ref=image_id).all()
    desktop_list = Desktop.query.filter_by(image_ref=image_id).all()
    if course_list or desktop_list:
        return True
    else:
        return False

def get_flavor_by_desktopid(desktop_id):
    try:
        desktop = Desktop.query.filter_by(id=desktop_id).first()
        if not desktop:
            return ""
        flavor = Flavor.query.filter_by(ref_id=desktop.flavor_ref).first()
        if flavor:
            return flavor.description
        vm = OpenstackComputeService.get_server(desktop.vm_ref)
        flavor = OpenstackComputeService.get_flavor(vm.flavor['id'])
        return "%dCPU | %dM RAM | %dG Disk" % \
               (flavor.vcpus, flavor.ram, flavor.disk)
    except:
        LOG.exception("Get Flavor By VM Id Failed.")
        return ""


def get_console_by_vmid(vmid):
    try:
        # 获取vnc控制台
        return  utils.get_instance_console(vmid)
    except:
        return ""


@image.route('/image_list', methods=['GET'])
@login_required
def image_list():
    image_list = []
    using_image=[]
    os_info = {}
    try:
        user_permission = current_user.role.permissions
        image_list_generator = imageutils.list_of_image()
        form = ImageEditForm()
        for image in image_list_generator:
            # if (image.owner == current_user.id):
            # convert image utc update time to local time
            image_extra_specs = Image.query.filter_by(ref_id=image.id).first()
            if not image_extra_specs:
                image_extra_specs = Image()
                image_extra_specs.name = image.name
                image_extra_specs.ref_id = image.id
                user = User.query.filter_by(username='admin').first()
                image_extra_specs.owner_id = user.id
                image_extra_specs.visibility = 'public'
                db.session.add(image_extra_specs)
                db.session.commit()

            if user_permission != Permission.ADMINISTER:
                if image_extra_specs is not None:
                    if image_extra_specs.visibility == 'private':
                        if image_extra_specs.owner_id == current_user.id:
                            pass
                        else:
                            continue

            image_info = {}
            image_info['id'] = image.id
            image_info['name'] = image.name
            if getattr(image, 'os_type', None) is not None:
                image_info['os_type'] = image.os_type
            if getattr(image, 'updated_at') is not None:
                image_info['updated_at']=timeutils.convert_to_tz(iso8601.parse_date(image.updated_at, timeutils.UTC), timeutils.LOCAL)
            if getattr(image, 'created_at') is not None:
                image_info['created_at'] =timeutils.convert_to_tz(iso8601.parse_date(image.created_at, timeutils.UTC), timeutils.LOCAL)
            image_info['size'] = image.size
            image_info['status'] = image.status
            if image_extra_specs is not None:
                image_info['owner_id'] = image_extra_specs.user.username
                image_info['description'] = image_extra_specs.description
                image_info['visibility'] = image_extra_specs.visibility
            else:
                image_info['owner_id'] = 'admin'
                image_info['description'] = ''
                image_info['visibility'] = 'public'
                image_extra_specs = Image()
                image_extra_specs.ref_id = image.id
                image_extra_specs.name = image.name
                user = User.query.filter_by(username='admin').first()
                image_extra_specs.owner_id = user.id
                db.session.add(image_extra_specs)
                db.session.commit()
            image_list.append(image_info)
            if check_img_using(image.id):
                using_image.append(image.id)

            #info = OpenstackImageService.get_image_metadata(image.id)
            #OS = info['os_distro'] + ' ' + info['os_version']
            OS = ''
            os_info[image.id] = OS
    except Exception as e:
        LOG.error("Get Image List Failed: %s" % e)
    return render_template('teachers/image/image_list.html', image_list=image_list,
                           using_image=using_image, os_info=os_info, form=form)


@image.route('/update_image', methods=['POST'])
@login_required
def update_image():
    image_edit_form = ImageEditForm()
    result = {}
    result['status'] = 'fail'
    if image_edit_form.validate_on_submit():
        try:
            image_list_generator = imageutils.list_of_image()
            for image in image_list_generator:
                if image.name == image_edit_form.imagename.data \
                        and image.id != image_edit_form.imageid.data:
                    result['status'] = 'existed'
                    return jsonify(**result)

            if image_edit_form.imagevisibility.data == True:
                visibility = 'public'
            else:
                visibility = 'private'
            image_extra_specs = Image.query.filter_by(ref_id=image_edit_form.imageid.data).first()
            if image_extra_specs:
                image_extra_specs.name = image_edit_form.imagename.data
                image_extra_specs.description = image_edit_form.imagedescription.data
                image_extra_specs.visibility = visibility
            else:
                image_extra_specs = Image()
                image_extra_specs.name = image_edit_form.imagename.data
                image_extra_specs.ref_id = image_edit_form.imageid.data
                image_extra_specs.name = image_edit_form.imagename.data
                image_extra_specs.owner_id = current_user.id
                image_extra_specs.description = image_edit_form.imagedescription.data
                image_extra_specs.visibility = visibility
            db.session.add(image_extra_specs)
            db.session.commit()
            LOG.info("Update Image Successfully: %s " % image_edit_form.imageid.data)
            ua_logger.info(current_user, "成功更新镜像: %s" % image_edit_form.imageid.data)
            result['status'] = 'success'
        except Exception as e:
            LOG.error("Update Image Failed： %s " % e)
    return jsonify(**result)


@image.route('/delete_image', methods=['POST'])
@login_required
def delete_image():
    ids = request.values.getlist('imageIds[]')
    error_list = []
    result ={}
    if ids is not None:
        try:
            for imageid in ids:
                course_list = Course.query.filter_by(image_ref=imageid).all()
                if course_list:
                    error_list.append(imageid)
                    continue
                desktop_list = Desktop.query.filter_by(image_ref=imageid).all()
                if desktop_list:
                    error_list.append(imageid)

            if error_list != []:
                result['status'] = "using"
            else:
                for imageid in ids:
                    OpenstackImageService.delete_image(imageid)
                    image = Image.query.filter_by(ref_id=imageid).first()
                    if image:
                        db.session.delete(image)
                        db.session.commit()
                    ua_logger.info(current_user, "成功删除镜像: %s" % imageid)
                result['status'] = 'success'
        except Exception as ex:
            LOG.error("Delete Image Fail: %s" % ex)
            result['status'] = 'fail'
        return jsonify(**result)


@image.route('/image_generator', methods=['GET'])
@login_required
def image_generator():
    try:
        user = User.query.filter_by(id=current_user.id).first()
        if not user.is_administrator():
            instance_list = Desktop.query.filter_by(desktop_type=DesktopType.TEMPLATE, owner_id=user.id).all()
        else:
            instance_list = Desktop.query.filter_by(desktop_type=DesktopType.TEMPLATE).all()
        flavor_list = OpenstackComputeService.list_flavors()

        image_list = imageutils.list_of_image()

        networks = OpenstackNetworkService.list_networks()
        network_list = []
        for network in networks.get("networks"):
            if not network["router:external"]:
                network_list.append(network)
        form = LaunchInstanceForm()
        return render_template('teachers/image/image_generator.html',
                               instance_list=instance_list,
                               flavor_list=flavor_list,
                               image_list=image_list,
                               network_list=network_list,
                               DesktopState=DesktopState,
                               get_flavor_by_desktopid=get_flavor_by_desktopid,
                               get_console_by_vmid=get_console_by_vmid,
                               form=form)
    except Exception as e:
        LOG.error("Get Image Generator Info Fail: %s" % e)
    return render_template('teachers/image/image_generator.html')


@image.route('/launch_instance', methods=['POST'])
@login_required
def launch_instance():
    try:
        result ={}
        result['status'] = 'fail'
        launch_instance_form = LaunchInstanceForm()

        if launch_instance_form.validate_on_submit():
            image_id = launch_instance_form.launch_imageid.data
            instance_name = launch_instance_form.instance_name.data
            flavor_id = launch_instance_form.image_flavor.data
            network_ref = launch_instance_form.network_ref.data

            # 检查是否存在相同的实例名称或桌面名称
            if Desktop.query.filter_by(name=instance_name).first():
                result['status'] = 'existed'
            else:
                # 创建实例
                valid, instance_name = utils.create_instance(instance_name, image_id,
                                                 flavor_id, network_ref, current_user.id)
                if valid:
                    result['status'] = "success"
                    ua_logger.info(current_user, "生成实例: %s" % instance_name)
                else:
                    result['status'] = "fail"
    except Exception as ex:
        LOG.error("Launch Instance Failed: %s" %  ex)
        result['status'] = 'fail'
    return jsonify(**result)


@image.route('/delete_instance', methods=['POST'])
@login_required
def delete_instance():
    result = {}
    result['status'] = 'fail'
    try:
        vmid = request.values.get('vmid')
        vmid_name = vmid.split('|')
        vmid = vmid_name[0]
        name = vmid_name[1]
        instance = Desktop.query.filter_by(vm_ref=vmid).first()
        if not instance:
            instance = Desktop.query.filter_by(name=name).first()
        desktop = Desktop.query.filter_by(vm_ref=vmid).first()
        if not desktop and instance:
            result['vmname'] = instance.name
            db.session.delete(instance)
            db.session.commit()
            result['status'] = 'success'
            ua_logger.info(current_user, "删除实例: %s" % instance.name)
        elif utils.delete_instance(vmid) == "success":
            result['status'] = 'success'
            result['vmname'] = instance.name
            ua_logger.info(current_user, "删除实例: %s" % instance.name)
        else:
            result['status'] = 'fail'
    except Exception as ex:
        LOG.error("Delete Instance Failed: %s" %  ex)
        result['status'] = 'fail'
    return jsonify(**result)


@image.route('/create_snapshot', methods=['POST'])
@login_required
def create_snapshot():
    result = {}
    result['status'] = 'fail'
    try:
        vmid = request.values.get('create_snapshot_vmid')
        name = request.values.get('snapshot_name')
        snapshot_description = request.values.get('snapshot_description', '')
        if not vmid or not name:
            return jsonify({'status': 'fail',
                            'data': 'parameter not provided'})
        #检查是否有重复的镜像名称
        # images_list = OpenstackImageService.list_images()
        images_list = imageutils.list_of_image()
        existedFlag = False
        for image in images_list:
            if image.name == name:
                existedFlag = True
        if existedFlag:
            result['status'] = 'exist'
        else:
            if utils.create_snapshot(vmid, name,current_user.id,
                                     snapshot_description):
                time.sleep(15)
                ua_logger.info(current_user, "成功创建快照: %s_%s" % (vmid, name))
                result['status'] = 'success'
            else:
                result['status'] = "fail"
    except Exception as ex:
        LOG.error("Create_snapshot Failed: %s" % ex)
        result['status'] = 'fail'
    return jsonify(**result)


@image.route('/power_on', methods=['POST'])
@login_required
def power_on():
    result = {}
    result['status'] = 'fail'
    try:
        vmid = request.values.get('vmid')
        # 开启线程启动虚拟机
        valid, instance_name = utils.power_on(vmid)
        if valid:
            result['status'] = "success"
            ua_logger.info(current_user, "开启镜像实例: %s" % vmid)
        else:
            result['status'] = "fail"
    except:
        LOG.exception("Power on Instance Failed: %s" % vmid)
        result['status'] = 'fail'
    return jsonify(**result)


@image.route('/power_off', methods=['POST'])
@login_required
def power_off():
    result = {}
    result['status'] = 'fail'
    try:
        vmid = request.values.get('vmid')
        valid, instance_name = utils.power_off(vmid)
        if valid:
            result['status'] = "success"
            ua_logger.info(current_user, "关闭镜像实例: %s" % vmid)
        else:
            result['status'] = "fail"
    except:
        LOG.exception("Power off Instance Failed: %s" % vmid)
        result['status'] = 'fail'
    return jsonify(**result)


@image.route('/image_instance_list', methods=['POST'])
@login_required
def image_instance_list():
    result = []
    try:
        #instance_ids = request.values.getlist('ids[]')
        #instance_names = request.values.getlist('names[]')
        #print(instance_names)
        instance_list = Desktop.query.filter_by(desktop_type=DesktopType.TEMPLATE).all()

        for instance in instance_list:
            #db.session.refresh(instance)
            instance_info = {}
            instance_response_format = {}
            instance_info['vmid'] = instance.vm_ref
            instance_info['status'] = instance.desktop_state
            instance_info['name'] = instance.name
            image_extra_specs = Image.query.filter_by(ref_id=instance.image).first()
            instance_info['image'] = image_extra_specs.name
            instance_info['description'] = get_flavor_by_desktopid(instance.id)
            instance_info['ip'] = instance.floating_ip

            try:
                #获取vnc控制台
                #instance_info['vnc_console'] = templateutils.vnc_console(instance.vmid)
                instance_info['console'] = utils.get_instance_console(instance.vm_ref)
            except:
                instance_info['console'] = ""
            instance_response_format['fields'] = instance_info
            result.append(instance_response_format)
        db.session.remove()
    except Exception as ex:
        LOG.error("Get Image Instance List Failed: %s" % ex)
        result = []
    return simplejson.dumps(result, encoding='utf-8')


@image.route('/get_instance_console', methods=['GET'])
@login_required
def get_instance_console(vmid):
    try:
        # 获取vm的vnc控制台
        instance_console = utils.get_instance_console(vmid)
    except Exception as ex:
        LOG.error("Get instance console Failed: %s" % ex)
        instance_console = None
    return render_template("teachers/image/instance_console.html",instance_console=instance_console)
