# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# monitor views
#
# 2016/7/25 luzh : Init


import importlib
import logging
import urllib
import simplejson
import urllib.request

from flask import render_template, url_for, request
from flask_login import login_required
from flask import make_response

import os
import sys
# sys.path.insert(0, os.path.abspath(os.path.join(
#     os.path.dirname(os.path.realpath(__file__)), '..', '..', '..')))
# print(sys.path)
from .. import db, app

from . import ganglia
from . import monitor

LOG = logging.getLogger(__name__)
GANGLIA_URL = app.config['GANGLIA_URL']


@monitor.route('/host_overview', methods=['GET'])
@login_required
def host_overview():
    """
        Show a list of Basic information
    :return:
    """
    cluster, host_detail = ganglia.ganglia_info()
    return render_template('monitor/host.html', tab='overview',
                           cluster=cluster, host_detail=host_detail)


@monitor.route('/host_performance', methods=['GET'])
@login_required
def host_performance():
    '''
    Show a list of Real-time monitoring
    '''
    try:
        cluster, host_detail = ganglia.ganglia_info()

        default_range = "hour"
        if len(host_detail) > 0:
            default_host = host_detail[0]["NAME"]
        else:
            default_host = ""
        sum_list = ("load_report", "cpu_report", "mem_report", "network_report")

        index_list = ["load_report", "cpu_report", "mem_report", "network_report",
                      "load_fifteen", "load_five", "load_one",
                      "cpu_aidle", "cpu_idle", "cpu_nice", "cpu_system", "cpu_user", "cpu_wio",
                      "mem_buffers", "mem_cached", "mem_free", "mem_shared", "swap_free",
                      "disk_free", "disk_total", "part_max_used",
                      "bytes_in", "bytes_out", "pkts_in", "pkts_out",
                      "proc_run", "proc_total"
                      ]
    except:
        LOG.exception("Fail to get host performance")
    return render_template('monitor/host.html',cluster = cluster, default_range = default_range, default_host = default_host,
                             sum_list = sum_list, host_detail = host_detail, index_list = index_list, tab = 'performance')

@monitor.route('/usage_makeImage/', methods=['GET'])
def usage_makeImage():
    try:
        cluster, host_detail = ganglia.ganglia_info()
        time_range = request.args.get("r", "hour")
        clustername = request.args.get("c", cluster["NAME"])
        load = request.args.get("q", "load_report")
        host = request.args.get("h", "default")
        indexlist = ("load_report", "cpu_report", "mem_report", "network_report")
        if host == "default":
            url = GANGLIA_URL + "/graph.php?z=median&g=" + load + "&c=" + \
            clustername + '&r=' + time_range
        elif load in indexlist:
            url = GANGLIA_URL + "/graph.php?z=median&g=" + load + "&c=" + \
            clustername + '&h=' + host + '&r=' + time_range + '&m=load_one'
        else:
            url = GANGLIA_URL + "/graph.php?z=medium&c=" + clustername + \
            '&m=' + load + '&h=' + host + '&r=' + time_range
        req = urllib.request.Request(url)
        webpage = urllib.request.urlopen(req)
        contentBytes = webpage.read()
        response = make_response(contentBytes)
        response.mimetype = "image/png"
    except:
        LOG.exception("Fail to get monitor information image")
    return response

