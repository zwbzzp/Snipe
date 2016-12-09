# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# comment
#
# 2016/6/1 0001 Jay : Init

from flask.ext.wtf import Form
from wtforms import StringField, SelectField
from wtforms.validators import data_required, mac_address

from ...models import Place


def choice_of_places():
    return [(place.id, place.name) for place in Place.query.all()]


class PlaceForm(Form):
    name = StringField('课室名称', validators=[data_required()])
    address = StringField('课室地址', validators=[data_required()])


class TerminalForm(Form):
    place_id = SelectField('选择课室', choices=[], coerce=int)
    seat_number = StringField('座位号', validators=[data_required()])
    mac_address = StringField('MAC地址', validators=[mac_address()])
    description = StringField('终端描述', validators=[data_required()])

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.place_id.choices = choice_of_places()
