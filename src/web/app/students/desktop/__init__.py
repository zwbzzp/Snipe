# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# comment
#
# 2016/4/12 qinjinghui : Init
__author__ = 'qinjinghui'


from flask import Blueprint

desktop = Blueprint('students_desktop', __name__)

from . import views
