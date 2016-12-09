# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# comment
#
# 2016/2/17 fengyc : Init

import os
import sys

sys.path.append(os.path.abspath(os.path.pardir(os.path.pardir(__file__))))

from . import create_celery

celery = create_celery()

