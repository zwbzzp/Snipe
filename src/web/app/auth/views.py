# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# auth views
#
# 2016/2/18 fengyc : Init

import time
from flask import redirect, render_template, url_for, request, flash, jsonify, current_app, session, g
from flask.ext.login import login_user, login_required, logout_user, current_user
from flask.ext.principal import Principal, Identity, AnonymousIdentity, \
    identity_changed, identity_loaded, RoleNeed, UserNeed
from sqlalchemy import or_
from . import auth
from .. import db, app
from .forms import LoginForm, RegisterForm, ChangeEmailForm, ChangePasswordForm, \
    PasswordResetRequestForm, PasswordResetForm
from ..models import User
from ..email import send_email
from .principal import AdminTypeNeed, StudentTypeNeed, TeacherTypeNeed, TerminalTypeNeed, CourseAllNeed
import logging
from ..log.utils import UserActionLogger

LOG = logging.Logger(__name__)
ua_logger = UserActionLogger()


@auth.before_app_request
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
            identity.provides.add(TeacherTypeNeed())
            identity.provides.add(StudentTypeNeed())
        if current_user.role.name == 'Teacher':
            identity.provides.add(StudentTypeNeed())
            courses = current_user.courses
            for course in courses:
                identity.provides.add(CourseAllNeed(course.id))
        if current_user.role.name == 'Terminal':
            identity.provides.add(TerminalTypeNeed())


@auth.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        # WARN always query a user by email, then by username
        user = User.query.filter(or_(User.email == form.username_email.data,
                                     User.username == form.username_email.data)).first()

        if user is not None and user.verify_password(form.password.data):
            if not user.is_active:
                flash("用户处于禁用状态禁止登录")
                LOG.error("用户处于禁用状态禁止登录")
                return redirect(url_for('auth.login'))

            login_user(user, form.remember_me.data)

            # Tell Flask-Principal the identity changed
            obj = current_app._get_current_object()
            identity_changed.send(current_app._get_current_object(),
                                  identity=Identity(user.id))

            ua_logger.info(user, "登录系统")
            LOG.info("%s登录系统" % user.fullname)
            return redirect(request.args.get('next') or url_for('main.index'))
        LOG.error("错误用户名或密码")
        flash('错误用户名或密码')
        return redirect(url_for('auth.login'))
    return render_template('auth/login.html', login_title='云晫云课室',
                           year=time.strftime('%Y', time.localtime(time.time())), form=form)


@auth.route('/download', methods=['GET', 'POST'])
def download():
    return render_template('download.html', login_title='云晫云课室',
                           year=time.strftime('%Y', time.localtime(time.time())))


@auth.route('/logout')
@login_required
def logout():
    ua_logger.info(current_user, "退出系统")
    LOG.info("%s退出系统" % current_user.fullname)
    logout_user()

    # Remove session keys set by Flask-Principal
    for key in ('identity.name', 'identity.auth_type'):
        session.pop(key, None)

    # Tell Flask-Principal the user is anonymous
    identity_changed.send(current_app._get_current_object(),
                          identity=AnonymousIdentity())
    flash('您已退出登录')
    return redirect(url_for('main.index'))


@auth.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if current_user.verify_password(form.old_password.data):
            current_user.password = form.password.data
            db.session.add(current_user)
            db.session.commit()
            flash('Your password has been updated.')
            LOG.info("%s 's password has been updated." % current_user.fullname)
            return redirect(url_for('main.index'))
        else:
            flash('Invalid password.')
            LOG.error('Invalid password.')
    return render_template("auth/change_password.html", form=form)


@auth.route('/reset', methods=['GET', 'POST'])
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
                           'auth/email/reset_password',
                           user=user, token=token,
                           next=request.args.get('next'))
                flash('邮件已发送，请查收并重设密码')
                return redirect(url_for('auth.login'))
            except Exception as e:
                flash('邮件发送异常，请重试或联系管理员')
                LOG.exception('邮件发送异常')
                return redirect(url_for('auth.login'))
    else:
        if form.errors.get('email') is not None:
            flash(form.errors.get('email'))
            LOG.error(form.errors.get('email'))
    return render_template('auth/reset_password.html', login_title='云晫云课室',
                           year=time.strftime(
                               '%Y', time.localtime(time.time())),
                           form=form)


@auth.route('/reset/<token>', methods=['GET', 'POST'])
def password_reset(token):
    if not current_user.is_anonymous:
        return redirect(url_for('main.index'))
    form = PasswordResetForm()
    if form.validate_on_submit():
        user = User.query.filter(or_(User.email == form.username_email.data,
                                     User.username == form.username_email.data)).first()
        if user is None:
            LOG.error("用户不存在")
            return redirect(url_for('main.index'))
        if user.reset_password(token, form.password.data):
            LOG.info('重置密码成功，请使用新密码登录.')
            flash('重置密码成功，请使用新密码登录.')
            return redirect(url_for('auth.login'))
        else:
            LOG.error("用户修改密码失败")
            return redirect(url_for('main.index'))
    else:
        if form.errors.get('email') is not None:
            LOG.error(form.errors.get('email'))
            flash(form.errors.get('email'))
        elif form.errors.get('password') is not None:
            LOG.error(form.errors.get('password')[0])
            flash(form.errors.get('password')[0])
    return render_template('auth/reset_password.html', login_title='云晫云课室',
                           year=time.strftime(
                               '%Y', time.localtime(time.time())),
                           form=form)


@auth.route('/change-email', methods=['GET', 'POST'])
@login_required
def change_email_request():
    form = ChangeEmailForm()
    if form.validate_on_submit():
        if current_user.verify_password(form.password.data):
            new_email = form.email.data
            token = current_user.generate_email_change_token(new_email)
            send_email(new_email, 'Confirm your email address',
                       'auth/email/change_email',
                       user=current_user, token=token)
            flash('An email with instructions to confirm your new email '
                  'address has been sent to you.')
            LOG.info('An email with instructions to confirm new email '
                  'address has been sent to %s.' % current_user.fullname)
            return redirect(url_for('main.index'))
        else:
            LOG.error('Invalid email or password.')
            flash('Invalid email or password.')
    return render_template("auth/change_email.html", form=form)


@auth.route('/change-email/<token>')
@login_required
def change_email(token):
    if current_user.change_email(token):
        flash('Your email address has been updated.')
    else:
        flash('Invalid request.')
    return redirect(url_for('main.index'))


@auth.route('/admin_login', methods=['POST'])
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
        LOG.exception("Authenticate Exceptionally: %s" % e)
        result['status'] = "fail"
    return jsonify(**result)
