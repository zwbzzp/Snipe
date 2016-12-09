# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# comment
#
# 16-7-12 qinjinghui : Init


import time
from flask import redirect, render_template, url_for, request, flash, \
    abort, jsonify, current_app, session, g
from flask.ext.login import login_user, login_required, logout_user, current_user
from flask.ext.principal import Principal, Identity, AnonymousIdentity, \
    identity_changed, identity_loaded, RoleNeed, UserNeed
from sqlalchemy import or_
from . import account
from .. import db, app
from .forms import LoginForm, RegisterForm, ChangeEmailForm, ChangePasswordForm, \
    PasswordResetRequestForm, PasswordResetForm,UserCreateForm, UserUpdateForm
from ..models import User, Role
from ..email import send_email
from..randompsw import  get_random_password
from .principal import AdminTypeNeed, UserTypeNeed, BotTypeNeed
import logging


LOG = logging.Logger(__name__)



@account.before_app_request
def before_request():
    if current_user.is_authenticated:
        # current_user.ping()
        if not current_user.confirmed \
                and request.endpoint[:5] != 'auth.' \
                and request.endpoint != 'static':
            return redirect(url_for('auth.unconfirmed'))


@identity_changed.connect_via(app)
def on_identity_changed(sender, identity):
    # TODO: should implement logic that on identity changed
    pass


@identity_loaded.connect_via(app)
def on_identity_loaded(sender, identity):
    # Set the identity user object
    identity.user = current_user

    # Add the UserNeed to the identity
    # if hasattr(current_user, 'id'):
    #     identity.provides.add(UserNeed(current_user.id))

    # update the identity with the role that the user provides
    if hasattr(current_user, 'role'):
        identity.provides.add(RoleNeed(current_user.role.name))

    # update the identity with resource needs according to role
    if hasattr(current_user, 'role'):
        # load admin permission
        if current_user.role.name == 'Administrator':
            identity.provides.add(AdminTypeNeed())
            identity.provides.add(UserTypeNeed())
        if current_user.role.name == 'User':
            identity.provides.add(UserTypeNeed())
        if current_user.role.name == 'Bot':
            identity.provides.add(BotTypeNeed())



@account.route('/login', methods=['GET', 'POST'])
def login():
    test = request
    username = test.values.get("username_email")
    form = LoginForm()
    if form.validate_on_submit():
        # WARN always query a user by email, then by username
        user = User.query.filter(or_(User.email == form.username_email.data,
                                     User.username == form.username_email.data)).first()

        if user is not None and user.verify_password(form.password.data):
            if not user.is_active:
                flash("用户处于禁用状态禁止登录")
                return redirect(url_for('auth.login'))

            login_user(user, form.remember_me.data)

            # Tell Flask-Principal the identity changed
            obj = current_app._get_current_object()
            identity_changed.send(current_app._get_current_object(),
                                  identity=Identity(user.id))

            return redirect(request.args.get('next') or url_for('main.index'))
        flash('错误用户名或密码')
        return redirect(url_for('account.login'))
    return render_template('account/login.html', login_title='云晫License管理系统',
                           year=time.strftime('%Y', time.localtime(time.time())), form=form)


@account.route('/download', methods=['GET', 'POST'])
def download():
    return render_template('download.html', login_title='云晫云课室',
                           year=time.strftime('%Y', time.localtime(time.time())))


@account.route('/logout')
@login_required
def logout():
    logout_user()

    # Remove session keys set by Flask-Principal
    for key in ('identity.name', 'identity.auth_type'):
        session.pop(key, None)

    # Tell Flask-Principal the user is anonymous
    identity_changed.send(current_app._get_current_object(),
                          identity=AnonymousIdentity())
    flash('您已退出登录')
    return redirect(url_for('main.index'))


@account.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    result = {"status": "fail", "fail_list": [], "error_msg": ""}
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if current_user.verify_password(form.old_password.data):
            current_user.password = form.password.data
            current_user.origin_password = ""
            db.session.add(current_user)
            db.session.commit()
            result['status'] = 'success'
        else:
            result['error_msg'] = 'invalid_password'
    return jsonify(**result)

@account.route('/change_profile', methods=['GET', 'POST'])
@login_required
def change_profile():
    result = {"status": "fail", "fail_list": [], "error_msg": ""}
    try:
        email = request.values.get("email", "")
        phone = request.values.get("phone", "")
        current_user.email = email
        current_user.phone = phone
        db.session.add(current_user)
        db.session.commit()
        result['status'] = 'success'
    except Exception as ex:
        pass
    return jsonify(**result)


@account.route('/reset', methods=['GET', 'POST'])
def password_reset_request():
    # If the user can login, he/she knows the password. Thus he/she does need
    # to reset password. Users who forgot the password need this function.
    if not current_user.is_anonymous:
        return redirect(url_for('main.index'))
    form = PasswordResetRequestForm()
    if form.validate_on_submit():
        user = User.query.filter(or_(User.email == form.username_email.data,
                                     User.username == form.username_email.data)).first()
        if user:
            try:
                token = user.generate_reset_password_token()
                send_email(user.email, 'Reset Your Password',
                           'account/email/reset_password',
                           user=user, token=token,
                           next=request.args.get('next'))
                flash('邮件已发送，请查收并重设密码')
                return redirect(url_for('account.login'))
            except Exception as e:
                flash('邮件发送异常，请重试或联系管理员')
                return redirect(url_for('account.login'))
    else:
        if form.errors.get('email') is not None:
            flash(form.errors.get('email'))
    return render_template('account/reset_password.html', login_title='云晫License管理平台',
                           year=time.strftime(
                               '%Y', time.localtime(time.time())),
                           form=form)


@account.route('/reset/<token>', methods=['GET', 'POST'])
def password_reset(token):
    if not current_user.is_anonymous:
        return redirect(url_for('main.index'))
    form = PasswordResetForm()
    if form.validate_on_submit():
        user = User.query.filter(or_(User.email == form.username_email.data,
                                     User.username == form.username_email.data)).first()
        if user is None:
            return redirect(url_for('main.index'))
        if user.reset_password(token, form.password.data):
            flash('重置密码成功，请使用新密码登录.')
            return redirect(url_for('account.login'))
        else:
            return redirect(url_for('main.index'))
    else:
        if form.errors.get('email') is not None:
            flash(form.errors.get('email'))
        elif form.errors.get('password') is not None:
            flash(form.errors.get('password')[0])
    return render_template('account/reset_password.html', login_title='云晫云课室',
                           year=time.strftime(
                               '%Y', time.localtime(time.time())),
                           form=form)


@account.route('/change-email', methods=['GET', 'POST'])
@login_required
def change_email_request():
    form = ChangeEmailForm()
    if form.validate_on_submit():
        if current_user.verify_password(form.password.data):
            new_email = form.email.data
            token = current_user.generate_email_change_token(new_email)
            send_email(new_email, 'Confirm your email address',
                       'account/email/change_email',
                       user=current_user, token=token)
            flash('An email with instructions to confirm your new email '
                  'address has been sent to you.')
            return redirect(url_for('main.index'))
        else:
            flash('Invalid email or password.')
    return render_template("account/change_email.html", form=form)


@account.route('/change-email/<token>')
@login_required
def change_email(token):
    if current_user.change_email(token):
        flash('Your email address has been updated.')
    else:
        flash('Invalid request.')
    return redirect(url_for('main.index'))


@account.route('/admin_login', methods=['POST'])
@login_required
def admin_login():
    result = {}
    try:
        userid = request.values.get('userid')
        pasword = request.values.get('password')
        user = User.query.filter(or_(User.email == userid,
                                     User.username == userid)).first()

        if user is None:
            LOG.error("Authenticate Failed: Wrong Admin Name")
            result['status'] = "wrong_name"
            return jsonify(**result)

        if not user.verify_password(pasword):
            LOG.error("Authenticate Failed: Wrong Admin Password")
            result['status']="wrong_password"
            return jsonify(**result)

        if user.is_administrator():
            LOG.info("Authenticate Successfully")
            result['status'] = "success"
    except Exception as e:
        LOG.error("Authenticate Exceptionally: %s" % e)
        result['status'] = "fail"
    return jsonify(**result)


@account.route('/users', methods=['GET'])
@login_required
def users():
    role = Role.query.filter_by(name='User').first()
    users = User.query.filter_by(role=role).all()
    form = UserCreateForm()
    return render_template('account/user.html',users=users,form=form)

@account.route('/create_user/', methods=['POST'])
@login_required
def create_user():
    form = UserCreateForm()
    if form.validate_on_submit():
        role = Role.query.filter_by(name='User').first()
        new_user = User()
        new_user.username = form.username.data
        new_user.organization = form.organization.data
        new_user.email = form.email.data
        new_user.phone = form.phone.data
        new_user.origin_password = get_random_password()
        new_user.password = new_user.origin_password
        new_user.is_active = True
        new_user.confirmed = True
        new_user.role = Role.query.filter_by(name='User').first()
        db.session.add(new_user)
        db.session.commit()
        user = {
            'id': new_user.id,
            'username': new_user.username,
            'organization': new_user.organization,
            'email': new_user.email,
            'phone': new_user.phone,
            'is_active': new_user.is_active,
            'origin_password':new_user.origin_password
        }

        return jsonify({'status': 'success', 'data': user})
    return jsonify({
        'status': 'fail',
        'data': {'form_errors': form.errors}
    })


@account.route('/update_user_status', methods=['PUT'])
@login_required
def update_user_status():
    try:
        user_id = request.json.get("user_id")
        user_status = request.json.get("user_status")
        user = User.query.filter_by(id=user_id).first()
        user.is_active = user_status
        db.session.add(user)
        db.session.commit()
        return jsonify({'status': 'success',
                        'data': {'id': user.id, 'username': user.username,'is_active': user.is_active}})
    except:
        return jsonify({'status': 'fail',
                        'data': 'user not exist or super user'})


@account.route('/update_user', methods=['PUT'])
@login_required
def update_user():
    form = UserUpdateForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user:
            user.organization = form.organization.data
            user.email = form.email.data
            user.phone = form.phone.data
            db.session.add(user)
            db.session.commit()
            user = {
                'id': user.id,
                'username': user.username,
                'organization': user.organization,
                'email': user.email,
                'phone': user.phone,
                'is_active': user.is_active
            }
            return jsonify({'status': 'success',
                            'data': user})
        else:
            return jsonify({'status': 'fail',
                            'data': 'user not exist'})
    else:
        return jsonify({
            'status': 'fail',
            'data': {'form_errors': form.errors}
        })


@account.route('/delete_users', methods=['DELETE'])
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
        try:
            user = User.query.filter_by(id=user_id).first()
            username = user.username
            db.session.delete(user)
            db.session.commit()
            result_json['data']['success_list'].append(
                {'id': user_id,'username':username})
        except:
            result_json['data']['fail_list'].append(
                {'id': user.id, 'username':user.username})
    return jsonify(result_json)

