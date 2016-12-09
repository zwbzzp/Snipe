# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# comment
#
# 16-8-3 qinjinghui : Init


from flask.ext.wtf import Form
from wtforms import Field, StringField
from wtforms.validators import data_required

class MigrateDesktopForm(Form):
    desktop_vm_ref = StringField("Desktop VM Id", validators=[data_required(),])
    desktop_name = StringField("Desktop Name",validators=[data_required(),])
    desktop_srchost = StringField("Desktop Host",validators=[data_required(),])
    desktop_desthost = StringField("Desktop Dest Host",validators=[data_required(),])