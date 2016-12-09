# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# utils for api
#
# 20160407 lipeizhao: Create module.

import importlib
import json
from urllib.parse import urljoin
from urllib import request

from phoenix.cloud import compute
# from oslo_config import cfg
import phoenix.config as cfg

cloud_options = [
    cfg.StrOpt('broker_url', default='http://127.0.0.1:9001/',
               help='spice broker url'),
]

cfg.CONF.register_opts(cloud_options, group='spice')

CONF = cfg.CONF

##############################
# desktop information
##############################


def desktop_to_json(desktop, default_protocol='rdp'):
    if desktop:
        # TODO: default_connection_type should achieve from desktop
        json_desktop = {
            'id': str(desktop.id),
            'name': desktop.name,
            'status': 'using',
            'os_username': 'administrator',
            'os_password': 'admin123',
            'default_connection_type': default_protocol,
            'connection_info': []
        }

        # add rdp connection information if rdp is supported
        if desktop.floating_ip:
            connection_info = {'type': 'rdp',
                               'ip': desktop.floating_ip}
            json_desktop['connection_info'].append(connection_info)

        # add spice connection information if spice is supported
        spice_console_url = _get_spice_console_url(desktop.vm_ref)
        if spice_console_url:
            connection_info = {'type': 'spice',
                               'console_url': spice_console_url}
            json_desktop['connection_info'].append(connection_info)
        return json_desktop
    return None

##############################
# get spice console
##############################


def _get_spice_console_url(vm_id):
    try:
        console = compute.get_server_console(vm_id, 'spice', 'spice-html5')
    except:
        console = None

    if console:
        return console['console']['url']
    return None
