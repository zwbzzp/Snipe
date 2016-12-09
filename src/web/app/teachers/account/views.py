# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# comment
#
# 2016/4/7 Lipeizhao : Init

import logging

from flask import render_template, url_for, request, jsonify, abort, redirect, \
current_app, send_from_directory, request, make_response, flash, g
from flask.ext.login import login_required, current_user
from . import account
from .forms import UserCreateForm, UserUpdateForm,ResetPasswordForm
from ...models import User, Role
from ... import db, csrf
from flask.ext import excel
import pyexcel.ext.xls
import pyexcel.ext.xlsx
from ...auth.principal import admin_permission, admin_type_perm, teacher_type_perm, student_type_perm
from ..storage.utils import StorageAccountManager
from ..log.utils import UserActionLogger

LOG = logging.getLogger(__name__)
ua_logger = UserActionLogger()


@account.route('/users?role=<string:role_name>', methods=['GET'])
@login_required
def users(role_name):
    role = Role.query.filter_by(name=role_name).first()
    if role:
        # permission check
        if role.name == 'Administrator' and admin_type_perm.can():
            html_template = 'teachers/account/admin.html'
        elif role.name == 'Teacher' and teacher_type_perm.can():
            html_template = 'teachers/account/teacher.html'
        elif role.name == 'Student' and student_type_perm.can():
            html_template = 'teachers/account/student.html'
        else:
            abort(403)
        users = User.query.filter_by(role=role).all()
        form = UserCreateForm()
        return render_template(html_template, users=users, form=form, role=role.name)
    abort(404)


@account.route('/users/', methods=['POST'])
@login_required
def create_user():
    form = UserCreateForm()
    if form.validate_on_submit():
        role = Role.query.filter_by(name=form.role.data).first()

        # permission check
        if not (role.name == 'Administrator' and admin_type_perm.can()) \
                and not (role.name == 'Teacher' and teacher_type_perm.can()) \
                and not (role.name == 'Student' and student_type_perm.can()):
            abort(403)

        user_model = User()
        user_model.username = form.username.data
        user_model.fullname = form.fullname.data
        user_model.email = form.email.data
        user_model.password = form.password.data
        user_model.confirmed = True
        user_model.role = Role.query.filter_by(name=form.role.data).first()
        db.session.add(user_model)
        db.session.commit()
        user = {
            'id':user_model.id,
            'username':user_model.username,
            'fullname':user_model.fullname,
            'email':user_model.email,
            'is_active':user_model.is_active
        }
        ua_logger.info(current_user, "创建用户: %s" % user_model.username)
        return jsonify({'status': 'success',
                        'data': user})

    return jsonify({
        'status': 'fail',
        'data': {'form_errors': form.errors}
    })


@account.route('/users/', methods=['DELETE'])
@login_required
def delete_users():
    result_json = {
        'status': 'success',
        'data': {
            'success_list': [],
            'fail_list': []
        }
    }
    users = request.json
    for user_id in users:
        user = User.query.filter_by(id=user_id).first()

        if user:
            role = user.role
            # permission check
            if not (role.name == 'Administrator' and admin_type_perm.can()) \
                    and not (role.name == 'Teacher' and teacher_type_perm.can()) \
                    and not (role.name == 'Student' and student_type_perm.can()):
                abort(403)

            if not user.is_super_administrator():
                result_json['data']['success_list'].append(
                    {'id':user.id, 'username':user.username})

                # 删除其个人文件夹
                # FIXME: 由于每个用户在同一个服务器上只能有一个个人文件夹, 所以这里采用逐个删除, 而无需批量删除
                samba_accounts = user.samba_accounts.all()
                for samba_account in samba_accounts:
                    samba_server = samba_account.samba
                    if samba_server:
                        try:
                            storage_account_manager = StorageAccountManager(samba_server.ip, samba_server.administrator, samba_server.password)
                            if storage_account_manager.login():
                                # when delete success, return True, or False
                                ret = storage_account_manager.delete(samba_account.user_id)
                            
                                if not ret:
                                    current_app.logger.warn(
                                        "Delete %s's samba account which on [%s] fail" % (user, samba_server.ip))
                            else:
                                current_app.logger.warn(
                                        "Login samba server [%s] fail" % samba_server.ip)

                        except Exception as ex:
                            current_app.logger.exception(ex)

                    # 无论samba服务器的个人文件夹删除成功与否, 都删除数据库中的记录
                    db.session.delete(samba_account)

                ua_logger.info(current_user, "删除用户: %s" % user.username)
                db.session.delete(user)
                current_app.logger.info(
                    "Delete %s user %s" % (user.role.name, user))
            else:
                result_json['data']['fail_list'].append(
                    {'id': user.id, 'username': user.username})
                current_app.logger.warn(
                    "Delete an super user")
        else:
            result_json['data']['success_list'].append(
                {'id':user_id})
            current_app.logger.warn(
                "Delete an non-exists user with id %s" % user_id)
    db.session.commit()
    return jsonify(result_json)


@account.route('/users/<int:id>/status', methods=['PUT'])
@login_required
def update_user_status(id):
    status = request.json
    user = User.query.filter_by(id=id).first()

    if user:
        role = user.role
        # permission check
        if not (role.name == 'Administrator' and admin_type_perm.can()) \
                and not (role.name == 'Teacher' and teacher_type_perm.can()) \
                and not (role.name == 'Student' and student_type_perm.can()):
            abort(403)

        if not user.is_super_administrator():
            user.is_active = status
            db.session.add(user)
            db.session.commit()
            ua_logger.info(current_user, "更改了用户%s的状态" % user.username)
            current_app.logger.info("%s user %s" % ("Active" if status else "Deactive", user.fullname))
            return jsonify({'status': 'success',
                            'data': {'id':user.id, 'username':user.username, 'is_active':user.is_active} })
    current_app.logger.warn("%s an non-exists user with id %s" % ("Active" if status else "Deactive", id))
    return jsonify({'status': 'fail',
                    'data': 'user not exist or super user'})


@account.route('/users/<int:id>', methods=['PUT'])
@login_required
def update_user(id):
    form = UserUpdateForm()
    if form.validate_on_submit():
        user_model = User.query.filter_by(username=form.username.data).first()
        if user_model:
            role = user_model.role

            # permission check
            # if not (role.name == 'Administrator' and admin_type_perm.can()) \
            #         and not (role.name == 'Teacher' and teacher_type_perm.can()) \
            #         and not (role.name == 'Student' and student_type_perm.can()):
            #     abort(403)
            user_model.fullname = form.fullname.data
            user_model.email = form.email.data
            db.session.add(user_model)
            db.session.commit()
            ua_logger.info(current_user, "修改了用户%s的信息" % user_model.username)
            current_app.logger.info("User %s updated" % user_model.fullname)
            user = {
                'id': user_model.id,
                'username':user_model.username,
                'fullname': user_model.fullname,
                'email': user_model.email,
                'is_active': user_model.is_active
            }
            return jsonify({'status': 'success',
                            'data': user})
        else:
            return jsonify({'status': 'fail',
                            'data': 'user not exist'})
    return jsonify({
        'data': {'form_errors': form.errors},
        'status': 'fail',
    })


@account.route('/export_user?role=<string:role_name>', methods=['GET'])
@login_required
def export_user(role_name):
    role_ = Role.query.filter_by(name=role_name).first()

    if role_name == 'Teacher' and teacher_type_perm.can():
        title =  ('教师账号', '姓名', '电子邮箱')
    elif role_name == 'Student' and student_type_perm.can():
        title =  ('学生学号', '姓名', '电子邮箱')
    else:
        abort(403)

    # get all target users
    user_list = User.query.filter_by(role=role_) \
        .with_entities(User.username, User.fullname, User.email).all()
    user_list.insert(0, title)
    ua_logger.info(current_user, "批量导出用户列表")
    return excel.make_response_from_array(user_list, "xls")


@account.route('/upload_user', methods=['POST'])
@login_required
def upload_user():
    json = {
        'status': 'success',
        'data': {
            'insert': 0,
            'total': 0,
            'error_msg': "",
            'fail_list': [],
            'success_list': []
        }
    }

    file = request.files['file']
    role_name = request.values['role']
    role = Role.query.filter_by(name=role_name).first()

    # permission check
    if not (role.name == 'Teacher' and teacher_type_perm.can()) \
            and not (role.name == 'Student' and student_type_perm.can()):
        abort(403)

    if file is not None:
        try:
            if file.content_length > (5 * 1024 * 1024):
                json["status"] = "fail"
                json["data"]["error_msg"] = "too large"
                return make_response(jsonify(json))

            temp = file.filename.split(".")
            file_type = temp[len(temp) - 1]
            if file_type == "xls" or file_type == "xlsx":
                user_array = request.get_array(field_name='file')
                user_array.pop(0)
                json["data"]["total"] = len(user_array)
                for user_line in user_array:
                    form = UserCreateForm()
                    form.username.data=user_line[0]
                    form.fullname.data=user_line[1]
                    form.email.data=user_line[2]
                    form.password.data=user_line[3]
                    form.confirm.data=user_line[3]
                    form.role.data='Teacher'
                    if form.validate_on_submit():
                        newuser_model = User(username = user_line[0],
                                             fullname = user_line[1],
                                             email = user_line[2])
                        newuser_model.password = user_line[3]
                        newuser_model.role = role
                        db.session.add(newuser_model)
                        db.session.commit()
                        user = {
                            'id': newuser_model.id,
                            'username': user_line[0],
                            'fullname': user_line[1],
                            'email': user_line[2],
                            'is_active': newuser_model.is_active
                        }
                        json["data"]["success_list"].append(user)
                    else:
                        err_str = ''
                        for item in form.errors.values():
                            err_str += item[0]
                            break
                        error = {'username': user_line[0], 'fullname': user_line[1], 'email': user_line[2], 'info': err_str}
                        json["data"]['fail_list'].append(error)
                        
                user_count = len(json["data"]["success_list"])
                fail_count = len(json["data"]['fail_list'])

                json["data"]["insert"] = user_count
                ua_logger.info(current_user, "批量导入用户列表,成功%s个,失败%s个" % (user_count, fail_count))
                if fail_count > 0:
                    json['status'] = 'part_success'
                else:
                    json['status'] = 'success'
            else:
                json["status"] = "fail"
                json["data"]["error_msg"] = "type error"
        except Exception as e:
            json["status"] = "fail"
            json["data"]["error_msg"] = "exception"
    else:
        json["status"] = "fail"
        json["data"]["error_msg"] = "not post"
    return make_response(jsonify(json))


@account.route('/get_user_info', methods=['POST'])
def get_user_info():
    result = {}
    try:
        userid = request.values.get("userid")
        user = User.query.filter_by(username=userid).first()
        result['userid'] = user.username
        result['fullname'] = user.fullname
    except Exception as ex:
        LOG.error("Get User Info Failed: %s" % ex)
        result['status'] = "fail"
    return jsonify(**result)


@account.route('/auth_user/', methods=['POST'])
def auth_user():
    result ={}
    try:
        admin_id = request.values.get("adminID")
        admin_pwd = request.values.get("admin_password")
        user_id = request.values.get("user_id")
        user_pwd = request.values.get("user_password")
        administrator = User.query.filter_by(username=admin_id).first()
        if administrator and administrator.verify_password(admin_pwd):
            user = User.query.filter_by(username=user_id).first()
            if user and user.verify_password(user_pwd):
                ua_logger.info(current_user, "成功认证用户: %s" % user.username)
                result["status"] = "success"
            else:
                result["status"] = "user_fail"
        else:
            result["status"] = "admin_fail"
    except Exception as ex:
        LOG.error("Auth User Failed: %s" % ex)
        result["status"] = "fail"
    return jsonify(**result)


@account.route('/modify_password', methods=['PUT'])
@login_required
def modify_password():
    result_json = {
        'status': 'success',
        'data': {
            'success_list': [],
            'fail_list': []
        }
    }
    request_json = request.json
    users = request_json['selected_user']
    password = request_json['password']
    for user_id in users:
        user = User.query.filter_by(id=user_id).first()
        if user:
            role = user.role
            # permission check
            if not (role.name == 'Administrator' and admin_type_perm.can()) \
                    and not (role.name == 'Teacher' and teacher_type_perm.can()) \
                    and not (role.name == 'Student' and student_type_perm.can()):
                abort(403)

            user.password = password
            db.session.add(user)
            db.session.commit()
            current_app.logger.info("User %s changed password" % user.fullname)
            ua_logger.info(current_user, "重置了用户%s密码" % user.username)
            result_json['data']['success_list'].append(user.username)
        else:
            result_json['data']['fail_list'].append(user_id)
    if len(result_json['data']['fail_list']) > 0:
        result_json['status'] = 'fail'
    return jsonify(result_json)

@account.route('/userinfo')
@login_required
def userinfo():
    user_role = Role.query.filter_by(id=current_user.role_id).first().name
    return render_template("teachers/user.html", current_user=current_user, user_role=user_role)

@account.route('/reset_currentuserpassword', methods=['PUT'])
@login_required
def reset_currentuserpassword():
    result_json = {
        'status': 'success',
        'errorinfo': ''
    }
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user_model = current_user
        if User.verify_password(user_model,form.oldpasswd.data):
            if user_model:
                user_model.password = form.newpasswd.data
                db.session.add(user_model)
                db.session.commit()
                current_app.logger.info("User %s changed password" % current_user.fullname)
                ua_logger.info(current_user, "用户%s重置了密码" % current_user.fullname)
                result_json['status'] = 'success'
            else:
                result_json['status'] = 'fail'
                result_json['errorinfo'] = '密码修改过错中出现错误'
        else:
            result_json['status'] = 'fail'
            result_json['errorinfo'] = '请输入正确的原用户密码'
    else:
        result_json['status'] = 'fail'
        result_json['errorinfo'] = '密码修改过错中出现错误'
    return jsonify(result_json)
