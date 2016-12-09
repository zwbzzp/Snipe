# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# network blueprint
#
# 2016/7/7 chengkang : Init

from flask import Blueprint
from phoenix.cloud import network as OpenstackNetworkService
from ... import app

network = Blueprint('teachers_network', __name__)

from . import views

is_neutron_network = OpenstackNetworkService.is_neutron_network()
def network_context_processor():
    return dict(is_neutron_network=is_neutron_network)
app.context_processor(network_context_processor)

if is_neutron_network:
    from . import views_neutron