# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# comment
#
# 16-8-3 qinjinghui : Init

__author__ = 'qinjinghui'


from flask import Blueprint
from oslo_config import cfg
from .. import app

vmotion_opts = [
    cfg.BoolOpt('enable', 
                default=False,
                help='The switch used to open or close Vmotion'),
    cfg.StrOpt('zookeeper',
                default='127.0.0.1:2181',
                help='The address of zookeeper servers, use comma to seperate them'),
    cfg.StrOpt('ext_network_znode',
                default='/monitor/ext',
                help='The znode on zookeeper server which used to monitor public network'),
    cfg.StrOpt('mgmt_network_znode',
                default='/monitor/mgmt',
                help='The znode on zookeeper server which used to monitor management network'),
    cfg.IntOpt('service_state_refresh_interval',
                default=30,
                help="The refresh interval of the nova-compute services' state, default 30 seconds")
]

cfg.CONF.register_opts(vmotion_opts, group='vmotion')

vmotion = None
enable = cfg.CONF.vmotion.enable

def vmotion_context_processor():
    return dict(is_vmotion_enable=enable)

app.context_processor(vmotion_context_processor)

if enable:
    vmotion = Blueprint('vmotion', __name__)
    from . import views