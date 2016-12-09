# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# comment
#
# 2016/4/7 Lipeizhao : Init

import datetime
from flask.ext.wtf import Form
from wtforms import Field, StringField, SubmitField, FieldList, FormField,\
    DateField, IntegerField, SelectField, SelectMultipleField, DateTimeField, \
    FileField, PasswordField
from wtforms.fields.html5 import EmailField
from wtforms.validators import data_required, length, regexp, number_range, Email, EqualTo

from .validators import EmailUnique, AccountUnique


#################
# user form
class UserCreateForm(Form):
    username = StringField('Username', validators=[
        data_required(message='用户名未填'),
        length(1, 64, message='用户名过长'),
        AccountUnique()])
    fullname = StringField('Fullname', validators=[
        data_required(message='姓名未填'),
        length(1, 64, message='姓名过长')])
    role = StringField('Role', validators=[data_required(), length(1, 64)])
    email = EmailField('Email', validators=[
        data_required(message='邮箱未填'),
        Email(message='无效的邮箱'),
        EmailUnique()])
    password = PasswordField('New Password', validators=[length(5, 64),
        data_required(message='密码未填'),
        EqualTo('confirm', message='两次输入密码必须一致')])
    confirm = PasswordField('Repeat Password',validators=[length(5, 64),
        data_required(message='密码未填')])


class UserUpdateForm(Form):
    username = StringField('Username', validators=[data_required(), length(1, 64)])
    fullname = StringField('Fullname', validators=[data_required(), length(1, 64)])
    email = EmailField('Email', validators=[data_required(), Email(), EmailUnique('username')])


class ModifyPasswordForm(Form):
    password = PasswordField('New Password', validators=[length(5, 64),
        data_required(),
        EqualTo('confirm', message='Password must match')])
    confirm = PasswordField('Repeat Password', validators=[length(5, 64),
        data_required()])

class ResetPasswordForm(Form):
    oldpasswd = PasswordField('old Password', validators=[length(5, 64),
        data_required()])
    newpasswd = PasswordField('New Password', validators=[length(5, 64),
        data_required(),
        EqualTo('confirmpasswd', message='Password must match')])
    confirmpasswd = PasswordField('Repeat Password', validators=[length(5, 64),
        data_required()])


#################
# teacher form
class UploadTeacherFileForm(Form):
    file = FileField('File', validators=[data_required()])


#################
# student form
class UploadStudentFileForm(Form):
    file = FileField('File', validators=[data_required()])



