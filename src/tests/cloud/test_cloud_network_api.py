# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# cloud api unit tests
#
# 20160113 lipeizhao : Init

from tests import test
from tests import fixture as db_fixtures

from phoenix.cloud import image
from phoenix.cloud import network


class NetworkTestCase(test.TestCase):

    def setUp(self):
        super(NetworkTestCase, self).setUp()
        self.ctxt = None

    def test_list_networks(self):
        pass

    def tearDown(self):
        super(NetworkTestCase, self).tearDown()

