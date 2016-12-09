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
from .. import db
from . import storage
from .forms import  AddFtpServerForm, EditFtpServerForm, AddFtpAccountForm,\
    EditFtpAccountForm, AddSambaServerForm, EditSambaServerForm, AddSambaAccountForm,\
    EditSambaAccountForm
from ..models import FtpServer, FtpAccount, SambaServer, SambaAccount,Course,User
from . import utils
from ..common import password_utils
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
    return render_template('storage/share.html', ftp_list=ftp_list,user=current_user,using_ftp=using_ftp)


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
            LOG.exception("Add Ftp Server Failed: %s" % ex)
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
                LOG.info("Add Ftp Server successfully.")
            except Exception as ex:
                result['status'] = 'fail'
                LOG.exception("Add Ftp Server Exception: %s." % ex)
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
            LOG.info("Delete Ftp Server: %s" % ftp.name)
            result['status'] = 'success'
    except Exception as ex:
        LOG.exception("Delete Ftp Server Failed")
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
                    LOG.info("Update Ftp Server: %s " % ftp.name)
                    result['status'] = 'success'
    except Exception as ex:
        LOG.exception("Update Ftp Server Failed ")
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


    return render_template('storage/share_account.html',account_list=ftp_account_list,
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
                LOG.info("Add Ftp Account: %s_%s" % (course_id, ftp_id))
                result['status'] = 'success'
            else:
                result['status'] = 'existed'
    except Exception as ex:
        LOG.exception("Add Ftp Account Failed")
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
                    LOG.info("Update Ftp Account: %s_%s" % (course_id, ftp_server_id))
                    result['status'] = 'success'
    except Exception as ex:
        LOG.exception("Update Ftp Server Failed")
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
            LOG.info("Delete Ftp Account: %s_%s" % (ftp_account.course_id, ftp_account.ftp_server_id))
            result['status'] = 'success'
    except Exception as ex:
        LOG.exception("Delete Ftp Account Failed")
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
    return render_template('storage/personal.html',server_list=samba_server_list,using_samba=using_samba)


@storage.route('/add_personal_storage', methods=['POST'])
@login_required
def add_personal_storage():
    result = {}
    result['status'] = 'fail'
    try:
        add_samba_server_form = AddSambaServerForm()
        if add_samba_server_form.validate_on_submit():
            name = add_samba_server_form.name.data
            ip = add_samba_server_form.ip.data
            administrator = add_samba_server_form.administrator.data
            password = add_samba_server_form.password.data

            exist_server = SambaServer.query.filter_by(ip=ip).first()
            exist_name_server = SambaServer.query.filter_by(name=name).first()
            manager = StorageAccountManager(host=ip, user=administrator,
                                            passwd=password_utils.encrypt(password))

            if not exist_server and not exist_name_server and password:
                try:
                    if manager.login():
                        encrypt_pwd = password_utils.encrypt(password)
                        new_samba_server = SambaServer()
                        new_samba_server.name = name
                        new_samba_server.ip = ip
                        new_samba_server.administrator = administrator
                        new_samba_server.password = encrypt_pwd
                        db.session.add(new_samba_server)
                        db.session.commit()
                        ua_logger.info(current_user, "成功创建个人文件服务器: %s" % name)
                        LOG.info("Add Personal Storage: %s" % name)
                        result['status'] = 'success'
                    else:
                        result['status'] = 'pswd_error'
                except Exception as ex:
                    LOG.exception("Add Personal Storage Failed")
                    result['status'] = 'connect_fail'
            else:
                result['status'] = 'existed'
    except Exception as ex:
        LOG.exception("Add Personal Storage Failed")
        result['status'] = 'fail'
    return jsonify(**result)


@storage.route('/update_personal_storage', methods=['POST'])
@login_required
def update_personal_storage():
    result = {}
    result['status'] = 'fail'
    try:
        edit_samba_server_form = EditSambaServerForm()
        if edit_samba_server_form.validate_on_submit():
            samba_server_id = edit_samba_server_form.samba_id.data
            name = edit_samba_server_form.name.data
            ip = edit_samba_server_form.ip.data
            administrator = edit_samba_server_form.administrator.data
            password = edit_samba_server_form.password.data

            exist_server_list = SambaServer.query.filter_by(ip=ip).all()
            is_existed_flag = False
            for server in exist_server_list:
                if server.id != samba_server_id:
                    is_existed_flag = True
                    break
            exist_name_server = SambaServer.query.filter_by(name=name).first()
            if not is_existed_flag and not exist_name_server:
                samba_server = SambaServer.query.filter_by(id=samba_server_id).first()
                samba_server.name = name
                samba_server.ip = ip
                #samba_server.password = password_utils.encrypt(password)
                if samba_server.administrator != administrator or password:
                    samba_server.administrator = administrator
                    encrypt_pwd = password_utils.encrypt(password)
                    samba_server.password = encrypt_pwd
                    manager = StorageAccountManager(host=ip, user=administrator,
                                            passwd=encrypt_pwd)
                    try:
                        if manager.login():
                            result['status'] = 'success'
                        else:
                            db.session.rollback()
                            result['status'] = 'pswd_error'
                    except Exception as ex:
                        db.session.rollback()
                        LOG.exception("Connect Samba Server Failed" )
                        result['status'] = 'connect_fail'
                        return jsonify(**result)
                else:
                    result['status'] = 'success'
                db.session.add(samba_server)
                db.session.commit()
                ua_logger.info(current_user, "更新个人文件服务器: %s" % name)
                LOG.info("更新个人文件服务器: %s" % name)
            else:
                 result['status'] = 'existed'
    except Exception as ex:
        db.session.rollback()
        LOG.exception("Update Samba Server Failed" )
        result['status'] = 'fail'
    return jsonify(**result)


@storage.route('/delete_personal_storage', methods=['POST'])
@login_required
def delete_personal_storage():
    result = {}
    result['status'] = 'fail'
    try:
        samba_sever_ids = request.values.getlist('ids[]')
        if samba_sever_ids is not None:
            for samba_server_id in samba_sever_ids:
                samba_server = SambaServer.query.filter_by(id=samba_server_id).first()
                db.session.delete(samba_server)
                ua_logger.info(current_user, "成功删除个人文件服务器: %s" % samba_server.name)
                LOG.info("成功删除个人文件服务器: %s" % samba_server.name)
            db.session.commit()
            result['status'] = 'success'
    except Exception as ex:
        LOG.exception("Delete Samba Server Failed" )
        result['status'] = 'fail'
    return jsonify(**result)


@storage.route('/personal_account', methods=['GET'])
@login_required
def personal_account():
    samba__server_list = SambaServer.query.all()
    samba_account_list = SambaAccount.query.all()
    user_list = User.query.all()
    return render_template('storage/personal_account.html',
                           samba_list=samba__server_list,
                           account_list=samba_account_list,
                           user_list=user_list)


@storage.route('/add_personal_account', methods=['POST'])
@login_required
def add_personal_account():
    result = {}
    result['status'] = 'fail'
    try:
        add_samba_account_form = AddSambaAccountForm()
        if add_samba_account_form.validate_on_submit():
            samba_server_id = add_samba_account_form.samba.data
            user_id = add_samba_account_form.user.data
            quota = add_samba_account_form.quota.data

            exist_account = SambaAccount.query.filter_by(samba_server_id=samba_server_id,user_id=user_id).first()
            if not exist_account:
                samba_server = SambaServer.query.filter_by(id=samba_server_id).first()
                manager = StorageAccountManager(host=samba_server.ip, user=samba_server.administrator,
                                                passwd=samba_server.password)
                # if not (int(quota) == 0): form中已有判断
                try:
                    if manager.login():
                        password = password_utils.encrypt(utils.generate_random_passwd())
                        if manager.add(user_id, password, str(quota)+'G'):
                            manager.logout()
                            new_account = SambaAccount()
                            new_account.samba_server_id = samba_server_id
                            new_account.user_id = user_id
                            new_account.password = password
                            new_account.quota = str(quota)+'GB'
                            db.session.add(new_account)
                            db.session.commit()
                            result['status'] = 'success'
                            LOG.info("Add Personal Storage Account Successfully")
                            ua_logger.info(current_user, "成功添加个人文件夹账号: %s_%s" % (user_id, samba_server_id))
                        else:
                            result['status'] = 'post_fail'
                except Exception as ex:
                    LOG.exception("Add Personal Storage Account Failed")
                    result['status'] = 'connect_fail'
                # else:
                #     result['status'] = 'fail'
                #     LOG.info("Add Personal Storage Account Failed: Quota == 0")
            else:
                result['status'] = 'existed'
    except Exception as ex:
        LOG.exception("Add Personal Storage Account Failed")
        result['status'] = 'fail'
    return jsonify(**result)


@storage.route('/update_personal_account', methods=['POST'])
@login_required
def update_personal_account():
    result = {}
    result['status'] = 'fail'
    try:
        update_samba_account_form = EditSambaAccountForm()
        if update_samba_account_form.validate_on_submit():
            account_id = update_samba_account_form.account.data
            samba_server_id = update_samba_account_form.samba.data
            user_id = update_samba_account_form.user.data
            quota = update_samba_account_form.quota.data
            samba_account = SambaAccount.query.filter_by(id=account_id).first()
            # old_quota = samba_account.quota[:-2]
            if samba_account:
                samba_server = samba_account.samba
                manager = StorageAccountManager(host=samba_server.ip,
                                                user=samba_server.administrator,
                                                passwd=samba_server.password)
                try:
                    if manager.login():
                        if manager.update(samba_account.user.id,samba_account.password,str(quota) + 'G'):
                            manager.logout()
                            samba_account.quota = str(quota) + 'GB'
                            db.session.add(samba_account)
                            db.session.commit()
                            ua_logger.info(current_user, "成功更新个人文件夹账号: %s_%s" % (user_id, samba_server_id))
                            LOG.info("成功更新个人文件夹账号: %s_%s" % (user_id, samba_server_id))
                            result['status'] = 'success'
                        else:
                            result['status'] = 'post_fail'
                except Exception as ex:
                    LOG.exception("Update Personal Storage Account Failed")
                    result['status'] = 'connect_fail'
            else:
                result['status'] = 'fail' # samba_account若为None，报错，覆盖不到此分支
        else:
            # 当表单不合法时, 将错误信息返回给前端
            result['status'] = str(update_samba_account_form.errors)
    except Exception as ex:
        LOG.error("Update Personal Storage Account Failed: %s" % ex)
        result['status'] = 'fail'
    return jsonify(**result)


@storage.route('/delete_personal_account', methods=['POST'])
@login_required
def delete_personal_account():
    result = {}
    result['status'] = 'fail'
    try:
        samba_account_ids = request.values.getlist('ids[]')
        if samba_account_ids is not None:
            server_account_map = {}
            for samba_account_id in samba_account_ids:
                samba_account = SambaAccount.query.filter_by(id=samba_account_id).first()
                samba_server = server_account_map.get(samba_account.samba.id, None)
                if samba_server:
                    samba_server.append(samba_account.user.id)
                else:
                    server_account_map[samba_account.samba.id] = []
                    server_account_map[samba_account.samba.id].append(samba_account.user.id)

            for (samba_server_id, samba_account_list) in server_account_map.items():
                samba_server = SambaServer.query.filter_by(id=samba_server_id).first()
                manager = StorageAccountManager(host=samba_server.ip,
                                                user=samba_server.administrator,
                                                passwd=samba_server.password)
                try:
                    if manager.login():
                        for userid in samba_account_list:
                            if manager.delete(userid):
                                samba_account = SambaAccount.query.filter_by(
                                    user_id=userid).first()
                                db.session.delete(samba_account)
                                db.session.commit()
                                ua_logger.info(current_user, "成功删除个人文件夹账号: %s_%s" % (userid, samba_server_id))
                                LOG.info("成功删除个人文件夹账号: %s_%s" % (userid, samba_server_id))
                                result['status'] = 'success'
                            else:
                                result['status'] = 'post_fail'
                                return jsonify(**result)
                        manager.logout()
                    else:
                        result['status'] = 'pswd_error'
                except Exception as ex:
                    LOG.exception("Delete Samba Server Account Failed")
                    result['status'] = 'connect_fail'
                    return jsonify(**result)
    except Exception as ex:
        LOG.exception("Delete Samba Server Account Failed")
        result['status'] = 'fail'
    return jsonify(**result)


@storage.route('/upload_personal_account', methods=['POST'])
@login_required
def upload_personal_account():
    result = {"status": "success", "insert": 0, "total": 0, "fail_list": []}
    try:
        upload_file = request.files.get("file")
        if upload_file is not None: #判断无意义，upload_file不为None
            valid, msg= utils.judge_file(upload_file, 5)
            if not valid:
                result["status"] = msg
                return jsonify(**result)
        personal_account_info_array = request.get_array(field_name='file')
        personal_account_info_array.pop(0)
        samba_account_map = {}
        smaba_account_duplicate_record = {} #用于记录重复名单{"sambaip":{"userid": [count, [lineno]]}}
        result['total'] = len(personal_account_info_array)

        current_lineno = 1
        for personal_account_info in personal_account_info_array:
            samba_server_ip = personal_account_info[0]
            user_account_id = personal_account_info[1]
            quota = personal_account_info[2]
            current_lineno += 1 #从第2行开始
            # 用于统计导入名单中的重复行
            samba_records = smaba_account_duplicate_record.get(samba_server_ip, None)
            if samba_records:
                record = samba_records.get(user_account_id, None)
                if record:
                    record[0] += 1
                    record[1].append(current_lineno)
                else:
                    samba_records[user_account_id] = [1, [current_lineno]]
            else:
                smaba_account_duplicate_record[samba_server_ip] = {}
                smaba_account_duplicate_record[samba_server_ip][user_account_id] = [1, [current_lineno]]

            samba_server = SambaServer.query.filter_by(ip=samba_server_ip).first()
            if not samba_server:
                error = {}
                error = {'sambaip': samba_server_ip,
                         'userid': user_account_id,
                         'info': '个人文件服务器不存在, 行号%s' % current_lineno}
                result['fail_list'].append(error)
                continue

            is_valid, reason = utils.isquota_format(quota)
            if is_valid:
                # for example,"12.00",12 and 12.0 is valid
                quota = int(float(quota))
                if user_account_id:
                    if type(user_account_id) == float :
                        user_account_id = int(user_account_id)
                        user_account_id = str(user_account_id)
                user = User.query.filter_by(username=user_account_id).first()
                if not user:
                    error = {}
                    error = {'sambaip': samba_server_ip,
                             'userid': user_account_id,
                             'info': '用户ID不存在, 行号%s' % current_lineno}
                    result['fail_list'].append(error)
                    continue
                existed_account = SambaAccount.query.filter_by(samba_server_id=samba_server.id,user_id=user.id).first()
                if existed_account:
                    error = {}
                    error = {'sambaip': samba_server_ip,
                             'userid': user_account_id,
                             'info': '用户已经存在, 行号%s' % current_lineno}
                    result['fail_list'].append(error)
                    continue

                samba_item = samba_account_map.get(samba_server.id, None)
                password = password_utils.encrypt(utils.generate_random_passwd())
                if samba_item:
                    count = 0
                    lenth = len(samba_item)
                    while count < lenth:
                        if samba_item[count][0] == str(user.id):
                            break # 重复的账户合为1个
                        else:
                            count += 1
                    if lenth == count:
                        samba_item.append((str(user.id), password, str(quota) + "G"))
                    else:
                        samba_account_map[samba_server.id][count]=((str(user.id)), password, str(quota) + "G")
                else:
                    samba_account_map[samba_server.id] = []
                    samba_account_map[samba_server.id].append((str(user.id), password, str(quota) + "G"))
            else:
                error = {}
                error = {'sambaip': samba_server_ip,
                         'userid': user_account_id,
                         'info': "%s, 行号%s" % (reason or "未知原因", current_lineno)}
                result['fail_list'].append(error)

        for sambaip, records in smaba_account_duplicate_record.items():
            for userid, record in records.items():
                if record[0] > 1:
                    error = {"sambaip": sambaip,
                             "userid": userid,
                             "info": "有%s行重复名单, 行号为:%s" % (record[0], record[1])}
                    result['fail_list'].append(error)
                    # 当有多行重复的名单时, 不对这些行做创建工作
                    samba_server = SambaServer.query.filter_by(ip=sambaip).first()
                    user = User.query.filter_by(username=userid).first()
                    if samba_server and user:
                        accounts = samba_account_map.get(samba_server.id, None)
                        if accounts:
                            for account in accounts[:]:
                                if account[0] == str(user.id):
                                    accounts.remove(account)

        bat_result = utils.add_account_batch(samba_account_map)
        result["insert"] = bat_result['insert']
        result["fail_list"].extend(bat_result["fail_list"])
        
        if(len(result['fail_list']) > 0):
            result['status'] = "part fail"
        else:
            result['status'] = "success"
        ua_logger.info(current_user, "成功导入个人文件夹账号 %s 个,失败 %s 个" % (result["insert"], len(result['fail_list'])))
        LOG.info("Add Personal Storage Account Batchly %s 个,失败 %s 个" % (result["insert"], len(result['fail_list'])))
    except Exception as ex:
        LOG.exception("Add Personal Storage Account Batchly Failed")
        import traceback
        traceback.print_exc()
        result['status'] = 'fail'

    return jsonify(**result)