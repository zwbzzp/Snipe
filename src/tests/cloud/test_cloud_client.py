# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# cloud client unit tests
#
# 20160113 lipeizhao : Init

from tests import test

from phoenix.cloud.openstack.client import ClientManager

KEYSTONE_CLI = ClientManager().keystone_client
NOVA_CLI = ClientManager().nova_client
GLANCE_CLI = ClientManager().glance_client
NEUTRON_CLI = ClientManager().neutron_client


class ComputeTestCase(test.TestCase):

    def setUp(self):
        super(ComputeTestCase, self).setUp()
        self.ctxt = None

    def test_novaclient(self):
        results = NOVA_CLI.flavors.list()
        self.assertIsNotNone(results)

    def test_keystoneclient(self):
        results = KEYSTONE_CLI.users.list()
        self.assertIsNotNone(results)

    def test_glanceclient(self):
        results = GLANCE_CLI.images.list()
        self.assertIsNotNone(results)

    def test_neutronclient(self):
        results = NEUTRON_CLI.list_networks()
        self.assertIsNotNone(results)

    def test_swiftclient(self):
        pass

    def tearDown(self):
        super(ComputeTestCase, self).tearDown()
        pass

