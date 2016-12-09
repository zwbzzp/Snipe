# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# Setting
#
# 2016/3/17 lipeizhao : Init

from flask import Blueprint

setting = Blueprint('students_setting', __name__)

from ...models import Permission

@setting.app_context_processor
def inject_permissions():
     return dict(Permission=Permission)
