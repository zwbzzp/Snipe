# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# comment
#
# 2016/3/31 qinjinghui : Init
__author__ = 'qinjinghui'

from ... import db
from flask.ext.wtf import Form
from flask.ext.login import current_user
from wtforms import Field, StringField, SubmitField, FieldList, FormField,\
    DateField, IntegerField, BooleanField, SelectField,TextAreaField
from wtforms.widgets import TableWidget
from wtforms.validators import data_required, length, regexp, number_range
from phoenix.cloud import image as OpenstackImageService
from phoenix.cloud import compute as OpenstackComputeService
from phoenix.cloud import network as OpenstackNetworkService
from ...models import User, Image
from ...common import imageutils

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

class ImageEditForm(Form):
    imagename = StringField("Image Name", validators=[data_required(),
                                                      length(1,64)])
    imageid = StringField("Image ID",validators=[data_required(),
                                                 length(1,64)])
    # imageformat = StringField("Image Format", validators=[data_required(),
    #                                                       length(1,64)])
    imagevisibility = BooleanField("Image Visibility")
    imagedescription = TextAreaField("Image Description")


class LaunchInstanceForm(Form):
    instance_name = StringField("Instance Name", validators=[data_required(),
                                                             length(1, 64)])
    launch_imageid = SelectField("Image Id", validators=[data_required()],
                                 choices=[])
    image_flavor = SelectField("Flavor Id", validators=[data_required()],
                               choices=[])
    network_ref = SelectField('virtual net', validators=[data_required()],
                              choices=[], default=None)

    def __init__(self, *args, **kwargs):
        super(LaunchInstanceForm, self).__init__(*args, **kwargs)
        self.launch_imageid.choices = choices_of_images()
        self.image_flavor.choices = choices_of_flavors()
        self.network_ref.choices = choices_of_networks()


