# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# comment
#
# 16-7-14 qinjinghui : Init

from flask.ext.wtf import Form
from wtforms import Field, StringField, BooleanField, SubmitField, FieldList, FormField,\
    DateField, IntegerField, SelectField, SelectMultipleField, DateTimeField, \
    FileField, PasswordField,SubmitField
from wtforms.fields.html5 import EmailField
from wtforms.validators import DataRequired,data_required, Length,length, \
    regexp, Regexp,number_range, Email, EqualTo,ValidationError

from ..models import Instance, User,Role


def choices_of_users():
    role = Role.query.filter_by(name='User').first()
    user_list = User.query.filter_by(role=role).order_by("username").all()
    return [(i.id, i.username) for i in user_list]


class InstanceForm(Form):
    instancename = StringField('Instancename', validators=[DataRequired(), Length(1, 64)])
    user=IntegerField("User", validators=[data_required()])

    # user=SelectField("User", validators=[data_required()],
    #                              choices=[])
    max_vm = IntegerField('MaxVM',validators=[DataRequired(),number_range(0, 100000000)])
    max_image = IntegerField('MaxIMAGE',validators=[DataRequired(),number_range(0, 100000000)])
    max_user = IntegerField('MaxUSER',validators=[DataRequired(),number_range(0, 100000000)])
    max_vcpu = IntegerField('MaxVCPU',validators=[DataRequired(),number_range(0, 100000000)])
    max_vmem = IntegerField('MaxVMEM',validators=[DataRequired(),number_range(0, 100000000)])
    max_vdisk = IntegerField('MaxVDISK',validators=[DataRequired(),number_range(0, 100000000)])
    expired_time = DateField('ExpiredTime', validators=[data_required()],format='%Y-%m-%d')

    # def __init__(self, *args, **kwargs):
    #     super(InstanceForm, self).__init__(*args, **kwargs)
    #     self.user.choices = choices_of_users()


