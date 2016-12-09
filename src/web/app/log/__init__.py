# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# comment
#
# 2016/4/14 chengkang : Init

from flask import Blueprint

log = Blueprint('log', __name__)

from . import views
