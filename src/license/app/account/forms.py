# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# comment
#
# 16-7-12 qinjinghui : Init

from flask.ext.wtf import Form
from wtforms import Field, StringField, BooleanField, SubmitField, FieldList, FormField,\
    DateField, IntegerField, SelectField, SelectMultipleField, DateTimeField, \
    FileField, PasswordField,SubmitField
from wtforms.fields.html5 import EmailField
from wtforms.validators import DataRequired,data_required, Length,length, \
    regexp, Regexp,number_range, Email, EqualTo,ValidationError

from ..models import User
from .validators import EmailUnique, AccountUnique

class LoginForm(Form):
    username_email = StringField(id='input_username', validators=[DataRequired(),
                                                                  Length(1, 64)])
    password = PasswordField(id='input_password', validators=[DataRequired(),
                                                              Length(5, 64)])
    remember_me = BooleanField(label='下次自动登录')
    submit = SubmitField(id='login_btn',label='登 录')


class RegisterForm(Form):
    username = StringField('Username', validators=[DataRequired(), Length(1, 64),
        Regexp('^[A-Za-z0-9_.]*$', 0, 'Username must have only letters, '
                                      'numbers, dots or underscores')])
    email = StringField('Email', validators=[DataRequired(), Length(1, 64),
                                             Email()])
    fullname = StringField('Fullname', validators=[DataRequired(), Length(1, 64)])
    password = PasswordField('Password', validators=[DataRequired(),Length(5, 64),
        EqualTo('password2', message='Passwords must match')])
    password2 = PasswordField('Confirm password', validators=[DataRequired(),Length(5, 64)])
    submit = SubmitField('Register')

    def validate_email(self, field):
        if User.query.filter_by(email=field.data).first():
            raise ValidationError('Email already registered.')

    def validate_username(self, field):
        if User.query.filter_by(username=field.data).first():
            raise ValidationError('Username already registered.')


class ChangePasswordForm(Form):
    old_password = PasswordField('Old password', validators=[DataRequired(),Length(5, 64)])
    password = PasswordField('New password', validators=[DataRequired(), Length(5, 64),
                              EqualTo('password2', message='Passwords must match')])
    password2 = PasswordField('Confirm new password',
                              validators=[DataRequired(), Length(5, 64)])
    submit = SubmitField('Update Password')


class PasswordResetRequestForm(Form):
    username_email = StringField('注册邮箱', validators=[DataRequired(),
                                                     Length(1, 64)])
    submit = SubmitField('发送验证邮件')

    def validate_username_email(self, field):
        if User.query.filter_by(email=field.data).first() is None and \
                User.query.filter_by(username=field.data).first() is None:
            error_dict = { 'email': '未注册的用户邮箱地址'}
            self.errors.update(error_dict)
            raise ValidationError('未注册的用户邮箱地址.')


class PasswordResetForm(Form):
    username_email = StringField('注册邮箱', validators=[DataRequired(),
                                                     Length(1, 64)])
    password = PasswordField('New Password', id='reset_password1', validators=[DataRequired(),
                                        Length(5, 64), EqualTo('password2', message='两次输入密码必须一致')])
    password2 = PasswordField('Confirm password', id='reset_password2',
                              validators=[DataRequired(), Length(5, 64)])
    submit = SubmitField('确认提交')

    def validate_username_email(self, field):
        if User.query.filter_by(email=field.data).first() is None and \
                User.query.filter_by(username=field.data).first() is None:
            error_dict = { 'email': '未注册的用户邮箱地址'}
            self.errors.update(error_dict)
            raise ValidationError('未注册的用户邮箱地址')


class ChangeEmailForm(Form):
    email = StringField('New Email', validators=[DataRequired(), Length(1, 64),
                                                 Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Update Email Address')

    def validate_email(self, field):
        if User.query.filter_by(email=field.data).first():
            raise ValidationError('Email already registered.')



#################
# user form
class UserCreateForm(Form):
    username = StringField('Username', validators=[
        data_required(message='用户名未填'),
        length(1, 64, message='用户名过长'),
        AccountUnique()])
    organization = StringField('Organization', validators=[
        data_required(message='所属公司/机构名称未填'),
        length(1, 30, message='所属公司/机构名称过长')])
    email = EmailField('Email', validators=[
        data_required(message='邮箱未填'),
        Email(message='无效的邮箱'),
        EmailUnique()])
    phone = StringField('Phone', validators=[ ])


class UserUpdateForm(Form):
    username = StringField('Username', validators=[data_required(), length(1, 64)])
    organization = StringField('Organization', validators=[data_required(),
                                                           length(1, 30)])
    email = EmailField('Email', validators=[data_required(), Email(), EmailUnique('username')])
    phone = StringField('Phone', validators=[])