# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# Cloud module
#
# 20160121 fengyingcai : Init
# 20160127 lipeizhao : Implementation

import phoenix.config as cfg

cloud_options = [
    cfg.StrOpt('backend', default='openstack',
               help='cloud backend'),
]

cfg.CONF.register_opts(cloud_options, group='cloud')

CONF = cfg.CONF
