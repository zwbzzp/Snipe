# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# comment
#
# 2016/2/26 fengyc : Init

import sys
import os

from base import FlaskTest
from novaclient.client import Client

class NovaTest(FlaskTest):
    def setUp(self):
        super(NovaTest, self).setUp()
        os_version = os.environ.get('OS_COMPUTE_API_VERSION') or '2.0'
        os_tenant_name = os.environ.get('OS_TENANT_NAME')
        os_username = os.environ.get('OS_USERNAME')
        os_password = os.environ.get('OS_PASSWORD')
        os_auth_url = os.environ.get('OS_AUTH_URL')
        self.client = Client(os_version, os_username, os_password, os_tenant_name, os_auth_url)

    def test_flavors_list(self):
        flavors = self.client.flavors.list()
        self.assertIsNotNone(flavors)

    def test_servers_list(self):
        servers = self.client.servers.list()
        if len(servers) > 0:
            s = servers[0]
            print(s)