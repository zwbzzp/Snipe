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
from ..models import UserActionLog, SystemRunningLog
from .utils import parse_date_range
from flask.ext.sqlalchemy import sqlalchemy
import simplejson

LOG = logging.getLogger(__name__)


@log.route('/user_action', methods=['GET', 'POST'])
@login_required
def user_action_logs():
    return render_template('log/user_action_log.html')


@log.route('/user_action_table', methods=['GET', 'POST'])
def user_action_log_table():
    col_map = {"0": "created_at",
               "1": "userid",
               "2": "message"}
    result_list = []

    sEcho = request.args.get('sEcho', "1")
    iDisplayStart = request.args.get('iDisplayStart', '0')
    iDisplayLength = request.args.get('iDisplayLength', '10')
    sSearch = request.args.get('sSearch', '')
    iSortCol = request.args.get('iSortCol_0', '0')
    sSortDir = request.args.get('sSortDir_0', '')

    date_range = request.args.get('date_range')
    if date_range == None:
        start_dt = datetime.datetime(1900, 1, 1)
        end_dt = datetime.datetime(2200, 1, 1)
    else:
        start_dt, end_dt = parse_date_range(date_range)

    sort_col = col_map[iSortCol]
    if sSortDir == "desc":
        sort_col += " desc"

    if sSearch == '' or sSearch is None:
        logs = UserActionLog.query.filter(
            UserActionLog.created_at >= start_dt, UserActionLog.created_at < end_dt).order_by(sort_col)
    else:
        logs = UserActionLog.query.filter(UserActionLog.created_at >= start_dt, UserActionLog.created_at < end_dt,
                                          sqlalchemy.or_(UserActionLog.userid.contains(sSearch), UserActionLog.message.contains(sSearch))).order_by(sort_col)
    page_index = int(iDisplayStart) // int(iDisplayLength)

    paginator = logs.paginate(page_index + 1, int(iDisplayLength), False)
    temp_log_list = paginator.items
    for log_item in temp_log_list:
        item = {}
        item["created_at"] = log_item.created_at.strftime("%Y-%m-%d %H:%M:%S")
        item["userid"] = log_item.userid
        item["message"] = log_item.message
        result_list.append(item)

    ret_data = {"sEcho": sEcho,
                "iTotalRecords": str(logs.count()),
                "iTotalDisplayRecords": str(logs.count()),
                "aaData": result_list}

    return jsonify(ret_data)


@log.route('/test_session', methods=['GET', 'POST'])
def test_session():
    return "success"


@log.route('/system_running', methods=['GET', 'POST'])
@login_required
def system_running_logs():
    return render_template('log/system_running_log.html')


@log.route('/system_running_table', methods=['GET', 'POST'])
def system_running_log_table():
    col_map = {"0": "created_at",
               "1": "message"}
    result_list = []

    sEcho = request.args.get('sEcho', "1")
    iDisplayStart = request.args.get('iDisplayStart', "0")
    iDisplayLength = request.args.get('iDisplayLength', "10")
    sSearch = request.args.get('sSearch', '')
    iSortCol = request.args.get('iSortCol_0', '0')
    sSortDir = request.args.get('sSortDir_0', '')

    date_range = request.args.get('date_range')
    if date_range == None:
        start_dt = datetime.datetime(1900, 1, 1)
        end_dt = datetime.datetime(2200, 1, 1)
    else:
        start_dt, end_dt = parse_date_range(date_range)

    sort_col = col_map[iSortCol]
    if sSortDir == "desc":
        sort_col += " desc"

    if sSearch == '' or sSearch is None:
        logs = SystemRunningLog.query.filter(
            SystemRunningLog.created_at >= start_dt, SystemRunningLog.created_at < end_dt).order_by(sort_col)
    else:
        logs = SystemRunningLog.query.filter(SystemRunningLog.created_at >= start_dt, SystemRunningLog.created_at < end_dt,
                                             SystemRunningLog.message.contains(sSearch)).order_by(sort_col)
    page_index = int(iDisplayStart) // int(iDisplayLength)
    paginator = logs.paginate(page_index + 1, int(iDisplayLength), False)
    temp_log_list = paginator.items
    for log_item in temp_log_list:
        item = {}
        item["created_at"] = log_item.created_at.strftime("%Y-%m-%d %H:%M:%S")
        item["message"] = log_item.message
        result_list.append(item)

    ret_data = {"sEcho": sEcho,
                "iTotalRecords": str(logs.count()),
                "iTotalDisplayRecords": str(logs.count()),
                "aaData": result_list}

    return jsonify(ret_data)
