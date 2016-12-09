# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# module init
#
# 20160407 lipeizhao: Create module.

from flask import Blueprint

api = Blueprint('api', __name__)

from . import authentication, users, terminals, desktops, errors
