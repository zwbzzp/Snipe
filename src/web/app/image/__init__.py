# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# comment
#
# 2016/3/31 qinjinghui : Init
__author__ = 'qinjinghui'


from flask import Blueprint

image = Blueprint('image', __name__)

from . import views
