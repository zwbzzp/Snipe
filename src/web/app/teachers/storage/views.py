# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# comment
#
# 2016/4/22 qinjinghui : Init
__author__ = 'qinjinghui'

import logging

from flask import render_template, request, jsonify,g
from flask.ext.login import current_user
from flask.ext.login import login_required
from ... import db
from . import storage
from .forms import  AddFtpServerForm, EditFtpServerForm, AddFtpAccountForm,\
    EditFtpAccountForm, AddSambaServerForm, EditSambaServerForm, AddSambaAccountForm,\
    EditSambaAccountForm
from ...models import FtpServer, FtpAccount, SambaServer, SambaAccount,Course,User
from . import utils
from ...common import password_utils
from .utils import StorageAccountManager, check_ftp_using,check_samba_using
from ..log.utils import UserActionLogger

LOG = logging.getLogger(__name__)
ua_logger = UserActionLogger()


@storage.route('/share', methods=['GET'])
@login_required
def share():
    ftp_list = []
    if current_user.role.name == 'Administrator':
        ftp_list = FtpServer.query.all()

    if current_user.role.name == 'Teacher':
        ftp_list = FtpServer.query.filter_by(user_id=current_user.id).all()
    using_ftp=[]
    for ftp in ftp_list:
        if check_ftp_using(ftp.id):
            using_ftp.append(ftp.id)
    return render_template('teachers/storage/share.html', ftp_list=ftp_list,user=current_user,using_ftp=using_ftp)


@storage.route('/add_share', methods=['POST'])
@login_required
def add_share():
    ftp_server_form = AddFtpServerForm()
    result = {}
    result['status'] = 'fail'
    if ftp_server_form.validate_on_submit():
        ftp_server_name = ftp_server_form.name.data
        ftp_server_ip = ftp_server_form.ip.data
        ftp_server_port = ftp_server_form.port.data
        try:
            ftp_by_ip_port = FtpServer.query.filter_by(ip=ftp_server_ip,
                                             port=ftp_server_port).first()
            fty_by_name = FtpServer.query.filter_by(name=ftp_server_name).first()
        except Exception as ex:
            LOG.error("Add Ftp Server Failed: %s" % ex)
            result['status'] = 'fail'
            return jsonify(**result)

        if ftp_by_ip_port or fty_by_name:
            result['status'] = 'existed'
            LOG.error("Ftp Server is existed.")
        else:
            try:
                ftp = FtpServer()
                ftp.name = ftp_server_name
                ftp.ip = ftp_server_ip
                ftp.port = ftp_server_port
                ftp.user_id = current_user.id
                db.session.add(ftp)
                db.session.commit()
                result['status'] = 'success'
                ua_logger.info(current_user, "成功关联共享文件服务器: %s" % ftp.name)
                LOG.error("Add Ftp Server successfully.")
            except Exception as ex:
                result['status'] = 'fail'
                LOG.error("Add Ftp Server Exception: %s." % ex)
    return jsonify(**result)


@storage.route('/delete_share', methods=['POST'])
@login_required
def delete_share():
    result = {}
    result['status'] = 'fail'
    try:
        ftp_id_list = request.values.getlist("ids[]")
        if ftp_id_list:
            for id in ftp_id_list:
                ftp = FtpServer.query.filter_by(id=id).first()
                #还需要添加用户权限的检查
                db.session.delete(ftp)
            db.session.commit()
            ua_logger.info(current_user, "成功删除共享文件服务器: %s" % ftp.name)
            result['status'] = 'success'
    except Exception as ex:
        LOG.error("Delete Ftp Server Failed: %s" % ex)
        result['status'] = 'fail'
    return jsonify(**result)


@storage.route('/update_share', methods=['POST'])
@login_required
def update_share():
    result = {}
    result['status'] = 'fail'
    try:
        edit_share_server_form = EditFtpServerForm()
        if edit_share_server_form.validate_on_submit():
            ftp_id = edit_share_server_form.ftp_id.data
            name = edit_share_server_form.name.data
            ip = edit_share_server_form.ip.data
            port = edit_share_server_form.port.data

            ftp_by_ip_port = FtpServer.query.filter_by(ip=ip, port=port).first()
            ftp_by_name =  FtpServer.query.filter_by(name=name).first()
            if (ftp_by_ip_port and ftp_by_ip_port.id != ftp_id) or (
                    ftp_by_name and ftp_by_name.id != ftp_id):
                 result['status'] = 'existed'
            else:
                ftp = FtpServer.query.filter_by(id=ftp_id).first()
                if ftp:
                    ftp.name = name
                    ftp.port = port
                    ftp.ip = ip
                    db.session.add(ftp)
                    db.session.commit()
                    ua_logger.info(current_user, "成功更新共享文件服务器: %s" % ftp.name)
                    result['status'] = 'success'
    except Exception as ex:
        LOG.error("Update Ftp Server Failed: %s " % ex)
        result['status'] = 'fail'
    return jsonify(**result)


@storage.route('/share_account', methods=['GET'])
@login_required
def share_account():
    #需要添加角色和用户的过滤
    ftp_account_list = []
    if current_user.role.name == 'Administrator':
        ftp_account_list = FtpAccount.query.all()
        ftp_list = FtpServer.query.all()
        course_list = Course.query.all()

    if current_user.role.name == 'Teacher':
        ftp_list = FtpServer.query.filter_by(user_id=current_user.id).all()
        for ftp in ftp_list:
            ftp_account_list_for_this_ftp =  FtpAccount.query.filter_by(ftp_server_id=ftp.id).all()
            ftp_account_list.append(ftp_account_list_for_this_ftp)
        course_list = Course.query.filter_by(owner_id=current_user.id).all()


    return render_template('teachers/storage/share_account.html',account_list=ftp_account_list,
                           course_list=course_list,ftp_list=ftp_list)


@storage.route('/add_share_account', methods=['POST'])
@login_required
def add_share_account():
    result = {}
    result['status'] = "fail"
    try:
        add_share_account_form = AddFtpAccountForm()
        if add_share_account_form.validate_on_submit():
            course_id = add_share_account_form.course.data
            ftp_id = add_share_account_form.ftp.data
            username = add_share_account_form.username.data
            password = add_share_account_form.password.data

            ftp = FtpServer.query.filter_by(id=ftp_id).first()
            if not utils.check_ftp_login(str(ftp.ip), ftp.port, username,
                                         password):
                result['status'] = "ftp_fail"
                return jsonify(**result)

            account = FtpAccount.query.filter_by(ftp_server_id=ftp_id, course_id=course_id, username=username).first()
            if not account:
                new_ftp_account = FtpAccount()
                new_ftp_account.ftp_server_id = ftp_id
                new_ftp_account.course_id = course_id
                new_ftp_account.username = username
                new_ftp_account.password = password_utils.encrypt(password)
                db.session.add(new_ftp_account)
                db.session.commit()
                ua_logger.info(current_user, "成功关联共享文件夹账号: %s_%s" % (course_id, ftp_id))
                result['status'] = 'success'
            else:
                result['status'] = 'existed'
    except Exception as ex:
        LOG.error("Add Ftp Account Failed: %s" % ex)
        result['status'] = "fail"
    return jsonify(**result)


@storage.route('/update_share_account', methods=['POST'])
@login_required
def update_share_account():
    result = {}
    result['status'] = 'fail'
    try:
        edit_share_account_form = EditFtpAccountForm()
        if edit_share_account_form.validate_on_submit():
            account_id = edit_share_account_form.account_id.data
            ftp_server_id = edit_share_account_form.ftp.data
            course_id = edit_share_account_form.course.data
            username = edit_share_account_form.username.data
            password = edit_share_account_form.password.data

            ftp = FtpServer.query.filter_by(id=ftp_server_id).first()
            if not utils.check_ftp_login(str(ftp.ip), ftp.port,
                                         username, password):
                result['status'] = "ftp_fail"
                return jsonify(**result)

            existed_ftp_account = FtpAccount.query.filter_by(ftp_server_id=ftp_server_id,
                                                             course_id=course_id,
                                                             username=username).first()
            if existed_ftp_account:
                result['status'] = 'existed'
            else:
                ftp_account = FtpAccount.query.filter_by(id=account_id).first()
                if ftp_account:
                    ftp_account.ftp_server_id = ftp_server_id
                    ftp_account.course_id = course_id
                    ftp_account.username = username
                    ftp_account.password = password_utils.encrypt(password)
                    db.session.add(ftp_account)
                    db.session.commit()
                    ua_logger.info(current_user, "成功更新共享文件夹账号: %s_%s" % (course_id, ftp_server_id))
                    result['status'] = 'success'
    except Exception as ex:
        LOG.error("Update Ftp Server Failed: %s " % ex)
        result['status'] = 'fail'
    return jsonify(**result)


@storage.route('/delete_share_account', methods=['POST'])
@login_required
def delete_share_account():
    result = {}
    result['status'] = 'fail'
    try:
        ftp_account_list = request.values.getlist("ids[]")
        if ftp_account_list:
            for id in ftp_account_list:
                ftp_account = FtpAccount.query.filter_by(id=id).first()
                db.session.delete(ftp_account)
            db.session.commit()
            ua_logger.info(current_user, "成功删除共享文件夹账号: %s_%s" % (ftp_account.course_id, ftp_account.ftp_server_id))
            result['status'] = 'success'
    except Exception as ex:
        LOG.error("Delete Ftp Account Failed: %s" % ex)
        result['status'] = 'fail'
    return jsonify(**result)


@storage.route('/personal', methods=['GET'])
@login_required
def personal():
    samba_server_list = SambaServer.query.all()
    using_samba=[]
    for samba in samba_server_list:
        if check_samba_using(samba.id):
            using_samba.append(samba.id)
    return render_template('teachers/storage/personal.html',server_list=samba_server_list,using_samba=using_samba)
