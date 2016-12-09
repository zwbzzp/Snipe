# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# edu blueprint
#
# 2016/2/18 fengyc : Init

from flask import Blueprint

edu = Blueprint('teachers_edu', __name__)

from . import views
