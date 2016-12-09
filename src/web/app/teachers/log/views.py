# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# comment
#
# 2016/4/14 chengkang : Init

import logging
import datetime
from . import log
from flask import render_template, jsonify, request
from flask.ext.login import login_required
from ...models import UserActionLog, SystemRunningLog
from .utils import parse_date_range
from flask.ext.sqlalchemy import sqlalchemy
import simplejson

LOG = logging.getLogger(__name__)


@log.route('/test_session', methods=['GET', 'POST'])
def test_session():
    return "success"
