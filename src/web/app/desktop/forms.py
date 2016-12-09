# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# comment
#
# 2016/4/12 qinjinghui : Init
__author__ = 'qinjinghui'

from flask.ext.wtf import Form
from .. import db
from flask.ext.login import current_user
from wtforms import Field, StringField, SubmitField, FieldList, FormField,\
    DateField, IntegerField, BooleanField, FileField, SelectField
from wtforms.widgets import TableWidget
from wtforms.validators import data_required, length, regexp, number_range
from phoenix.cloud import image as OpenstackImageService
from phoenix.cloud import compute as OpenstackComputeService
from phoenix.cloud import network as OpenstackNetworkService
from app.models import User, Image
from ..common import imageutils

def choices_of_users():
    user_list = User.query.all()
    # 如果是i.id会报错,因为页面的返回类型为str
    return [(i.username, i.username) for i in user_list]


def choices_of_images():
    return [(i.id, i.name) for i in imageutils.list_of_image()]


def choices_of_flavors():
    return [(i.id, i.name) for i in OpenstackComputeService.list_flavors()]

def choices_of_networks():
    networks = OpenstackNetworkService.list_networks()
    choices = []
    try:
        choices = [(i["id"], i["name"] or i["id"]) for i in networks.get("networks") if not i["router:external"]]
    except:
        # nova
        choices = [(i.id, i.label) for i in networks]
    return choices


class CreateStaticDesktopForm(Form):
    owner = SelectField("Owner",  validators=[data_required()], choices=[])
    template = SelectField("Image", validators=[data_required()], choices=[])
    flavor = SelectField("Flavor", validators=[data_required()], choices=[])
    network = SelectField("Network", validators=[data_required()], choices=[])

    def __init__(self, *args, **kwargs):
        super(CreateStaticDesktopForm, self).__init__(*args, **kwargs)
        self.owner.choices = choices_of_users()
        self.template.choices = choices_of_images()
        self.flavor.choices = choices_of_flavors()
        self.network.choices = choices_of_networks()


class FileUploadForm(Form):
    file = FileField("file", validators=[data_required()])

