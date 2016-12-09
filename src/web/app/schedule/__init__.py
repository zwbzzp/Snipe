# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# Schedule center
#
# 2016/3/1 fengyc : Init

from flask import Blueprint

schedule = Blueprint('schedule', __name__)

from . import views
