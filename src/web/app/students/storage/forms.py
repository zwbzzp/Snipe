# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# comment
#
# 2016/4/22 qinjinghui : Init
__author__ = 'qinjinghui'


from flask.ext.wtf import Form
from wtforms import Field, StringField, SubmitField, FieldList, FormField,\
    DateField, IntegerField, BooleanField
from wtforms.widgets import TableWidget
from wtforms.validators import data_required, length, regexp, number_range,IPAddress


class AddFtpServerForm(Form):
    name = StringField("Ftp Name", validators=[data_required(),
                                               length(1, 64)])
    ip = StringField("Ftp Ip",validators=[data_required(), IPAddress(),
                                          length(1, 64)])
    port = IntegerField("Ftp Port", validators=[data_required(),
                                                number_range(1, 65535)])


class EditFtpServerForm(Form):
    ftp_id = IntegerField("Ftp Id", validators=[data_required()])
    name = StringField("Ftp Name", validators=[data_required(),
                                               length(1, 64)])
    ip = StringField("Ftp Ip",validators=[data_required(), IPAddress(),
                                          length(1, 64)])
    port = IntegerField("Ftp Port", validators=[data_required(),
                                                number_range(1, 65535)])


class AddFtpAccountForm(Form):
    course = IntegerField("Course Id", validators=[data_required()])
    ftp = IntegerField("Ftp Id", validators=[data_required()])
    username = StringField("Ftp User Name", validators=[data_required(),
                                               length(1, 64)])
    password = StringField("Ftp User Password", validators=[data_required(),
                                               length(1, 64)])


class EditFtpAccountForm(Form):
    account_id = IntegerField("Account Id", validators=[data_required()])
    course = IntegerField("Course Id", validators=[data_required()])
    ftp = IntegerField("Ftp Id", validators=[data_required()])
    username = StringField("Ftp User Name", validators=[data_required(),
                                               length(1, 64)])
    password = StringField("Ftp User Password", validators=[data_required(),
                                               length(1, 64)])


class AddSambaServerForm(Form):
    name = StringField("Samba Server Name", validators=[data_required(),
                                               length(1, 64)])
    ip = StringField("Samba Server Ip",validators=[data_required(), IPAddress(),
                                          length(1, 64)])
    administrator = StringField("Samba Administrator Name", validators=[data_required(),
                                               length(1, 64)])
    password = StringField("Samba Administrator Password", validators=[data_required(),
                                               length(1, 64)])



class EditSambaServerForm(Form):
    samba_id = IntegerField("Samba Server Id", validators=[data_required()])
    name = StringField("Samba Server Name", validators=[data_required(),
                                               length(1, 64)])
    ip = StringField("Samba Server Ip",validators=[data_required(), IPAddress(),
                                          length(1, 64)])
    administrator = StringField("Samba Administrator Name", validators=[data_required(),
                                               length(1, 64)])
    password = StringField("Samba Administrator Password")


class AddSambaAccountForm(Form):
    samba = IntegerField("Samba Server Id", validators=[data_required()])
    user = IntegerField("User Id", validators=[data_required()])
    quota = IntegerField("Quota",validators=[data_required(),number_range(1, 30)])


class EditSambaAccountForm(Form):
    account = IntegerField("Samba Account Id", validators=[data_required()])
    samba = IntegerField("Samba Server Id", validators=[data_required()])
    user = IntegerField("User Id", validators=[data_required()])
    quota = IntegerField("Quota",validators=[data_required(),number_range(1, 30)])


