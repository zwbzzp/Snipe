# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# comment
#
# 16-7-9 qinjinghui : Init

from flask import Blueprint

account = Blueprint('account', __name__)

from . import views