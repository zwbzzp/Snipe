# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# comment
#
# 16-7-14 qinjinghui : Init


import datetime
import time
from flask import redirect, render_template, url_for, request, flash, \
    abort, jsonify, current_app, session, g
from flask.ext.login import login_user, login_required, logout_user, current_user
from flask.ext.principal import Principal, Identity, AnonymousIdentity, \
    identity_changed, identity_loaded, RoleNeed, UserNeed
from sqlalchemy import or_
from . import instance
from .. import db, app
from ..models import User,Role, Instance, InstanceStatus
from .forms import InstanceForm
from ..email import send_email
import logging
import os
import rsa
from binascii import hexlify,unhexlify
import hashlib

basedir = os.path.abspath(os.path.dirname(__file__))
basedir = os.path.join(basedir, '../')
KEY_ROOT = os.path.join(basedir, 'key')
DOWNLOAD_ROOT = os.path.join(basedir, 'static/license')


@instance.route('/instances', methods=['GET'])
@login_required
def instances():
    instance_list = []
    user_list = []
    forbidden_list = []
    instance_status = ""
    today = datetime.datetime.now()
    #Update Instance Status
    all_instance = Instance.query.all()
    for instance in all_instance:
        expired_time = instance.expired_time
        tmp = (expired_time - today).days
        if tmp < 0:
            instance.status = InstanceStatus.EXPIRED
            db.session.add(instance)
            db.session.commit()
        if instance.status == InstanceStatus.DOWNLOADERROR:
            now = datetime.datetime.now()
            last = instance.updated_at
            interval = (now -last).seconds
            if interval >= 600:
                instance.status = InstanceStatus.TODOWNLOAD
                instance.download = 0
                db.session.add(instance)
                db.session.commit()

    if current_user.is_administrator():
        role = Role.query.filter_by(name='User').first()
        user_list = User.query.filter_by(role=role).order_by("username").all()
        instance_list = Instance.query.order_by("updated_at").all()
        forbidden_list = Instance.query.filter(or_(
            Instance.status==InstanceStatus.TODOWNLOAD,
            Instance.status==InstanceStatus.DOWNLOADERROR)).all()
    else:
        instance_list = Instance.query.filter_by(
            user_id=current_user.id).order_by("updated_at").all()
    # info_list = {}
    # for instance in instance_list:
    #     info_list[instance] = instance.status
    form = InstanceForm()

    return render_template('instance/instance.html',
                           form=form, user_list=user_list,
                           instance_list=instance_list,
                           forbidden_list=forbidden_list,
                           InstanceStatus=InstanceStatus)

@instance.route('/add_instance', methods=['POST'])
@login_required
def add_instance():
    form = InstanceForm()
    if form.validate_on_submit() and current_user.is_administrator():
        new_instancename = form.instancename.data
        new_owner = form.user.data
        new_max_vm = form.max_vm.data
        new_max_user = form.max_user.data
        new_max_image = form.max_image.data
        new_max_vcpu = form.max_vcpu.data
        new_max_vmem = form.max_vmem.data
        new_max_vdisk = form.max_vdisk.data
        new_expired_time = form.expired_time.data

        if is_existed_instanceid(new_instancename):
            return jsonify({'status': 'fail', 'data': {'form_errors': {
                'instancename': '实例名已经存在'}}})
        else:
            new_instance = Instance()
            new_instance.instancename = new_instancename
            new_instance.user_id = new_owner
            new_instance.max_vm = new_max_vm
            new_instance.max_user = new_max_user
            new_instance.max_image = new_max_image
            new_instance.max_vcpu = new_max_vcpu
            new_instance.max_vmem = new_max_vmem
            new_instance.max_vdisk = new_max_vdisk
            new_instance.expired_time = new_expired_time
            new_instance.status = InstanceStatus.TOUPLOAD
            db.session.add(new_instance)
            db.session.commit()
            instance_info = {
                'id': new_instance.id,
                'instancename': new_instance.instancename,
                "user_id": new_instance.user_id,
                "username": new_instance.user.username,
                "organization": new_instance.user.organization,
                'mac': new_instance.mac,
                'sn': new_instance.serial_number,
                'status_chs': new_instance.get_status_str(),
                "stauts": new_instance.status,
                "expired_time": new_instance.expired_time.strftime("%Y-%m-%d"),
                "max_vm": new_instance.max_vm,
                "max_user": new_instance.max_user,
                "max_image": new_instance.max_image,
                "max_vcpu": new_instance.max_vcpu,
                "max_vmem": new_instance.max_vmem,
                "max_vdisk": new_instance.max_vdisk
            }
            return jsonify(
                {'status': 'success', 'data': instance_info})
    return jsonify({
        'status': 'fail',
        'data': {'form_errors': form.errors}
    })




@instance.route('/update_instance', methods=['PUT'])
@login_required
def update_instance():
    form = InstanceForm()
    if form.validate_on_submit() and current_user.is_administrator():
        new_instancename = form.instancename.data
        new_owner = form.user.data
        new_max_vm = form.max_vm.data
        new_max_user = form.max_user.data
        new_max_image = form.max_image.data
        new_max_vcpu = form.max_vcpu.data
        new_max_vmem = form.max_vmem.data
        new_max_vdisk = form.max_vdisk.data
        new_expired_time = form.expired_time.data

        new_instance = Instance.query.filter_by(instancename=new_instancename).first()

        if new_instance.status == InstanceStatus.TODOWNLOAD or \
                new_instance.status == InstanceStatus.DOWNLOADERROR:
            return jsonify({'status': 'fail', 'data': {'form_errors': {
                'instancename': '该实例不能被编辑'}}})

        new_instance.instancename = new_instancename
        new_instance.user_id = new_owner
        new_instance.max_vm = new_max_vm
        new_instance.max_user = new_max_user
        new_instance.max_image = new_max_image
        new_instance.max_vcpu = new_max_vcpu
        new_instance.max_vmem = new_max_vmem
        new_instance.max_vdisk = new_max_vdisk
        new_instance.expired_time = new_expired_time
        db.session.add(new_instance)
        db.session.commit()
        instance_info = {
            'id': new_instance.id,
            'instancename': new_instance.instancename,
            "user_id": new_instance.user_id,
            "username": new_instance.user.username,
            "organization": new_instance.user.organization,
            'mac': new_instance.mac,
            'sn': new_instance.serial_number,
            'status_chs': new_instance.get_status_str(),
            "stauts": new_instance.status,
            "expired_time": new_instance.expired_time.strftime("%Y-%m-%d"),
            "max_vm": new_instance.max_vm,
            "max_user": new_instance.max_user,
            "max_image": new_instance.max_image,
            "max_vcpu": new_instance.max_vcpu,
            "max_vmem": new_instance.max_vmem,
            "max_vdisk": new_instance.max_vdisk
        }
        return jsonify(
            {'status': 'success', 'data': instance_info})

    return jsonify({
        'status': 'fail',
        'data': {'form_errors': form.errors}
    })


@instance.route('/delete_instances', methods=['DELETE'])
@login_required
def delete_instances():
    result_json = {
        'status': 'success',
        'data': {
            'success_list': [],
            'fail_list': []
        }
    }
    instances = request.json
    for instance_id in instances:
        try:
            instance = Instance.query.filter_by(id=instance_id).first()
            instancename = instance.instancename
            db.session.delete(instance)
            db.session.commit()
            result_json['data']['success_list'].append(
                {'id': instance_id, 'instancename': instancename})
        except:
            result_json['data']['fail_list'].append(
                {'id': instance_id, 'instancename': instancename})
    return jsonify(result_json)


@instance.route('/upload_hostinfo', methods=['POST'])
@login_required
def upload_hostinfo():
    result = {"status": "fail", "fail_list": [], "error_msg": ""}
    try:
        upload_file = request.files.get("file")
        post_instanceid = request.values.get("instanceid", '')
        if upload_file.content_length > (1024 * 1024):
            result["error_msg"] = "too_large"
            return jsonify(**result)

        temp = upload_file.name.split(".")
        if len(temp) == 1:
            contents = upload_file.readlines()
            t_instancename = contents[0].decode().replace("\n","")
            t_mac = contents[1].decode().replace("\n", "")
            t_sn = contents[2].decode().replace("\n", "")
            decodekeys = contents[4:]
            decodekey = ""
            for line in decodekeys:
                decodekey += line.decode()
            instance = Instance.query.filter(or_(Instance.id==post_instanceid,Instance.instancename==post_instanceid)).first()
            if instance:
                post_instancename = instance.instancename
                if post_instancename == t_instancename:
                    vinzor_prikey_file = open(KEY_ROOT + "/private.pem", "r")
                    vinzor_prikey_data = vinzor_prikey_file.read()
                    vinzor_prikey = rsa.PrivateKey.load_pkcs1(vinzor_prikey_data)

                    decry_data = rsa.decrypt(unhexlify(contents[3].strip()), vinzor_prikey)

                    md5 = hashlib.md5()
                    md5.update(t_sn.encode())
                    psw = md5.hexdigest()[:64]

                    if (psw == decry_data.decode()):
                        instance.mac = t_mac
                        instance.serial_number = t_sn
                        instance.public_key = decodekey
                        instance.status = InstanceStatus.TODOWNLOAD
                        result["status"]="success"
                    else:
                        instance.status = InstanceStatus.INFOERROR
                        result["error_msg"] = "danger"
                    db.session.add(instance)
                    db.session.commit()
                else:
                    result["error_msg"] = "instanceid_error"
            else:
                result["error_msg"] = "not_exist"
    except Exception as ex:
        result['status'] = 'fail'
    return jsonify(**result)


@instance.route('/download_license', methods=['POST'])
@login_required
def download_license():
    result = {"status": "fail", "fail_list": [], "error_msg": ""}
    try:
        t_instanceid = request.values.get("instanceid", '')
        instance = Instance.query.filter(or_(Instance.id==t_instanceid,Instance.instancename==t_instanceid)).first()

        if instance:
            if instance.user_id == current_user.id or current_user.username == "anonymousrobot":
                downloadtimes = instance.download
                if downloadtimes == 5:
                    status = instance.status
                    if instance.status == InstanceStatus.TODOWNLOAD:
                        instance.status = InstanceStatus.DOWNLOADERROR
                        result["error_msg"] = "download_error"
                        db.session.add(instance)
                        db.session.commit()
                        return jsonify(**result)
                    else:
                        result["status"] = "fail"
                        return jsonify(**result)

                info = ""
                info += str(instance.max_vm) + "\n"
                info += str(instance.max_user) + "\n"
                info += str(instance.max_image) + "\n"
                info += str(instance.max_vcpu) + "\n"
                info += str(instance.max_vmem) + "\n"
                info += str(instance.max_vdisk) + "\n"
                info += instance.expired_time.strftime("%Y-%m-%d") + "\n"
                info += instance.mac + "\n"
                info += instance.serial_number + "\n"

                decodekey = instance.public_key
                p = decodekey.encode(encoding="utf-8")
                pubkey = rsa.PublicKey.load_pkcs1(p)
                info = info.encode(encoding='utf-8')
                crypto = rsa.encrypt(info, pubkey)
                crypto = hexlify(crypto).decode()
                lcfile = open(DOWNLOAD_ROOT + "/" + t_instanceid.upper() + "_LICENSE","w+")
                lcfile.write(crypto)
                lcfile.close()

                if downloadtimes != 0:
                    now = datetime.datetime.now()
                    last = instance.updated_at
                    interval = (now - last).seconds
                    if interval <= 30:
                        instance.download = downloadtimes + 1
                        db.session.add(instance)
                        db.session.commit()
                    # 两次下载间隔超过20分钟则重新计算次数
                    if interval >= 60*20:
                        instance.download = 1
                        db.session.add(instance)
                        db.session.commit()
                else:
                    instance.download = 1
                    db.session.add(instance)
                    db.session.commit()
                result['status'] = "success"
            else:
                result['status'] = 'fail'
        else:
            result['status'] = 'fail'
    except Exception as ex:
        result['status'] = 'fail'
    return jsonify(**result)


def is_existed_instanceid(instancename):
    instance = Instance.query.filter_by(instancename=instancename).first()
    if instance:
        return True
    else:
        return False



