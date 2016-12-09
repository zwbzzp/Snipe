# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# edu blueprint
#
# 2016/4/7 lipeizhao : Init

from flask import Blueprint

account = Blueprint('teachers_account', __name__)

from . import views
