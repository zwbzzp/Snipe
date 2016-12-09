# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# comment
#
# 2016/2/18 fengyc : Init

import datetime

from flask import render_template, request
from flask.ext.login import login_required, current_user
from . import main
from .utils import get_week_period_info_detail
from ..models import User, Course, Period
from ..common import timeutils


@main.route('/')
@login_required
def index():
    if current_user.role.name == 'Administrator':
        return admin_index()
    elif current_user.role.name == 'Teacher':
        return teachers_index()
    else:
        return students_index()


def admin_index():
    # TODO: add rbac here, different role give different index page content
    start_date_str = request.args.get('start_date', None)
    date = None
    if start_date_str is not None:
        date = datetime.datetime.strptime(start_date_str, '%Y-%m-%d').date()
    else:
        date = datetime.date.today()
    start_date = timeutils.get_week_start_date(date)
    end_date = timeutils.get_week_end_date(date)
    detail_table = get_week_period_info_detail(start_date, current_user)
    weekdays = range(1, 8)
    periods = Period.query.order_by(Period.start_time)
    date_span = {'start_date': start_date, 'end_date': end_date}
    return render_template('main/admin.html',
                           weekdays=weekdays,
                           periods=periods,
                           date_span=date_span,
                           detail_table=detail_table,
                           current_user=current_user)


def teachers_index():
    # TODO: add rbac here, different role give different index page content
    start_date_str = request.args.get('start_date', None)
    date = None
    if start_date_str is not None:
        date = datetime.datetime.strptime(start_date_str, '%Y-%m-%d').date()
    else:
        date = datetime.date.today()
    start_date = timeutils.get_week_start_date(date)
    end_date = timeutils.get_week_end_date(date)
    detail_table = get_week_period_info_detail(start_date, current_user)
    weekdays = range(1, 8)
    periods = Period.query.order_by(Period.start_time)
    date_span = {'start_date': start_date, 'end_date': end_date}
    return render_template('teachers/main/admin.html',
                           weekdays=weekdays,
                           periods=periods,
                           date_span=date_span,
                           detail_table=detail_table,
                           current_user=current_user)


def students_index():
    # TODO: add rbac here, different role give different index page content
    start_date_str = request.args.get('start_date', None)
    date = None
    if start_date_str is not None:
        date = datetime.datetime.strptime(start_date_str, '%Y-%m-%d').date()
    else:
        date = datetime.date.today()
    start_date = timeutils.get_week_start_date(date)
    end_date = timeutils.get_week_end_date(date)
    detail_table = get_week_period_info_detail(start_date, current_user)
    weekdays = range(1, 8)
    periods = Period.query.order_by(Period.start_time)
    date_span = {'start_date': start_date, 'end_date': end_date}
    return render_template('students/main/admin.html',
                           weekdays=weekdays,
                           periods=periods,
                           date_span=date_span,
                           detail_table=detail_table,
                           current_user=current_user)
