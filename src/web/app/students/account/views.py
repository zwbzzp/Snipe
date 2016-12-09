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
    return render_template("students/user.html", current_user=current_user, user_role=user_role)

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
