# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# cloud api unit tests
#
# 20160113 lipeizhao : Init

import time

from tests import test
from tests.fixture import cloud as cloud_fixture

from phoenix.cloud import compute
from phoenix.cloud import network


class ComputeServerTestCase(test.TestCase):
    """
    Should have existed image and flavor for testing purpose
    """
    def setUp(self):
        super(ComputeServerTestCase, self).setUp()
        self.ctxt = None

    @classmethod
    def setUpClass(cls):
        cloud_fixture.PrivateNetworkEnv().setUp()

    def test_create_and_get_server(self):
        self.useFixture(cloud_fixture.ServerEnv('create_get'))
        server_before = compute.get_server_by_name('test_server_create_get')
        server_get = compute.get_server(server_before.id)
        self.assertEqual(server_before.id, server_get.id)

    def test_list_servers(self):
        servers = compute.list_servers()
        self.assertIsNotNone(servers)

    def delete_server(self):
        self.useFixture(cloud_fixture.ServerEnv('delete'))
        server_before = compute.get_server_by_name('test_server_delete')
        self.assertIsNotNone(server_before.id)

        compute.delete_server(server_before.id)
        server_get = compute.get_server_by_name(server_before.name)
        self.assertIsNone(server_get)

    def test_suspend_and_resume_server(self):
        self.useFixture(cloud_fixture.ServerEnv('suspend'))
        server_before = compute.get_server_by_name('test_server_suspend')
        compute.suspend_server(server_before.id)
        pass_flag = self._check_server_status(server_before.id, ['SUSPENDING', 'SUSPENDED'])
        self.assertEqual(True, pass_flag)

        compute.resume_server(server_before.id)
        pass_flag = self._check_server_status(server_before.id, ['ACTIVE'])
        self.assertEqual(True, pass_flag)

    def test_soft_reboot_server(self):
        self.useFixture(cloud_fixture.ServerEnv('soft_reboot'))
        server_before = compute.get_server_by_name('test_server_soft_reboot')
        compute.reboot_server(server_before.id)
        pass_flag = self._check_server_status(server_before.id, ['REBOOT'])
        self.assertEqual(True, pass_flag)

    def test_hard_reboot_server(self):
        self.useFixture(cloud_fixture.ServerEnv('hard_reboot'))
        server_before = compute.get_server_by_name('test_server_hard_reboot')
        compute.reboot_server(server_before.id, False)
        pass_flag = self._check_server_status(server_before.id, ['HARD REBOOT', 'ACTIVE'])
        self.assertEqual(True, pass_flag)

    def test_pause_server(self):
        self.useFixture(cloud_fixture.ServerEnv('pause'))
        server_before = compute.get_server_by_name('test_server_pause')
        compute.pause_server(server_before.id)
        pass_flag = self._check_server_status(server_before.id, ['PAUSED'])
        self.assertEqual(True, pass_flag)

        compute.unpause_server(server_before.id)
        pass_flag = self._check_server_status(server_before.id, ['ACTIVE'])
        self.assertEqual(True, pass_flag)

    def test_stop_server(self):
        self.useFixture(cloud_fixture.ServerEnv('stop'))
        server_before = compute.get_server_by_name('test_server_stop')
        compute.stop_server(server_before.id)
        pass_flag = self._check_server_status(server_before.id, ['SHUTOFF'])
        self.assertEqual(True, pass_flag)

    def test_delete_server(self):
        self.useFixture(cloud_fixture.ServerEnv('delete'))
        server_before = compute.get_server_by_name('test_server_delete')
        compute.delete_server(server_before.id)
        server_after = compute.get_server_by_name('test_server_delete')
        self.assertEqual(getattr(server_after, 'OS-EXT-STS:task_state'), 'soft-deleting')

    def _check_server_status(self, server_id, status, time_out=30, sleep_time=3):
        sleep_time = sleep_time
        time_out = time_out
        time_pass = 0
        while time_pass < time_out:
            server_get = compute.get_server(server_id)
            if server_get.status in status:
                return True
            time_pass += sleep_time
            time.sleep(sleep_time)
        return False

    @classmethod
    def _delete_network(self, network_id, time_out=120, sleep_time=3):
        sleep_time = sleep_time
        time_out = time_out
        time_pass = 0
        while time_pass < time_out:
            try:
                network.delete_network(network_id)
                break
            except Exception as ex:
                time.sleep(sleep_time)
                time_pass += sleep_time

    def tearDown(self):
        super(ComputeServerTestCase, self).tearDown()
        servers = compute.list_servers()
        expected_servers = [server for server in servers if server.name.find('test_server') == 0]
        for s in expected_servers:
            compute.delete_server(s)

    @classmethod
    def tearDownClass(cls):
        network_name = 'test_network_private'
        expected_network = network.get_network_by_name(network_name)
        cls._delete_network(expected_network['id'])


class ComputeFlavorTestCase(test.TestCase):
    """
    Should have existed image and flavor for testing purpose
    """
    def setUp(self):
        super(ComputeFlavorTestCase, self).setUp()
        self.ctxt = None

    def test_list_flavor(self):
        flavors = compute.list_flavors()
        self.assertIsNotNone(flavors)

    def test_get_flavor(self):
        flavor = compute.create_flavor(name='test_flavor1',
                                       ram=4096,
                                       vcpus=2,
                                       disk=20)
        flavor_get = compute.get_flavor(flavor)
        self.assertEqual(flavor.id, flavor_get.id)

    def test_create_flavor(self):
        flavor = compute.create_flavor(name='test_flavor2',
                                       ram=4096,
                                       vcpus=2,
                                       disk=20)
        flavor_get = compute.get_flavor(flavor)
        self.assertEqual(flavor.id, flavor_get.id)

    def test_delete_flavor(self):
        flavor = compute.create_flavor(name='test_flavor3',
                                       ram=4096,
                                       vcpus=2,
                                       disk=20)

        compute.delete_flavor(flavor)
        flavors = compute.list_flavors()
        exist = False
        for f in flavors:
            if flavor.id == f.id:
                exist = True
        self.assertEquals(exist, False)

    def tearDown(self):
        super(ComputeFlavorTestCase, self).tearDown()
        flavors = compute.list_flavors()
        expected_flavors = [flavor for flavor in flavors if flavor.name.find('test_flavor') == 0]
        for f in expected_flavors:
            compute.delete_flavor(f)


