# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# comment
#
# 2016/3/15 luzih : Init

from ... import db
from flask.ext.wtf import Form
from flask.ext.login import current_user
from ...models import User, Image
from wtforms import Field, StringField, SubmitField, FieldList, FormField,\
    DateField, IntegerField, BooleanField, SelectField, DateTimeField
from wtforms.widgets import TableWidget
from wtforms.validators import data_required, length, regexp, number_range

from phoenix.cloud import compute as OpenstackComputeService
from phoenix.cloud import image as OpenstackImageService
from ...common import imageutils


def get_images_for_selectfield():
    return [(i.id, i.name) for i in imageutils.list_of_image()]

def get_flavors_for_selectfield():
    flavor_list =  []
    flavors = OpenstackComputeService.list_flavors()
    for flavor in flavors:
        flavor_list.append((flavor.id,
                            "%dCPU | %dM RAM | %dG Disk" %
                            (flavor.vcpus, flavor.ram,flavor.disk)))
    return flavor_list


class CourseTimeForm(Form):
    start_time = DateTimeField('开始时间', format='%H:%M')
    end_time = DateTimeField('结束时间', format='%H:%M')


class FlavorForm(Form):
    name = StringField(label='Name', validators=[data_required(), length(1, 64)])
    cpunum = IntegerField(label='CpuNum', validators=[data_required(),
                                                      number_range(1, 8)])
    ramnum = IntegerField(label='RamNum', validators=[data_required(),
                                                      number_range(512, 8196)])
    disknum = IntegerField(label='DiskNum', validators=[data_required(),
                                                        number_range(1, 512)])


class FlavorEditForm(FlavorForm):
    flavorid = StringField('FlavorId', validators=[data_required()])


class ParamForm(Form):
    free_desktop_switch = SelectField(label="是否开启",
                                      choices=(("True", '开启',),
                                               ("False", '关闭',)),
                                      validators=[data_required()])
    free_desktop_capacity = IntegerField(label="桌面数量",
                                         validators=[data_required()])
    free_desktop_flavor = SelectField(label="桌面配置",
                                      choices=[],
                                      validators=[data_required()])
    free_desktop_image = SelectField(label="桌面镜像",
                                     choices=[],
                                     validators=[data_required()])
    free_desktop_start_time = DateTimeField(label="开始时间",
                                            validators=[data_required()],
                                            format="%H:%M")
    free_desktop_stop_time = DateTimeField(label="结束时间",
                                           validators=[data_required()],
                                           format="%H:%M")

    def __init__(self, *args, **kwargs):
        super(ParamForm, self).__init__(*args, **kwargs)
        self.free_desktop_flavor.choices = get_flavors_for_selectfield()
        self.free_desktop_image.choices = get_images_for_selectfield()
