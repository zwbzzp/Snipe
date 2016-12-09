# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# auth blueprint
#
# 2016/2/18 fengyc : Init

from flask import Blueprint

auth = Blueprint('auth', __name__)

from . import views