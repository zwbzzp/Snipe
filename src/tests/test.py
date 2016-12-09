# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# Base classes for our unit tests
#
# 20160113 lipeizhao : Init

import testtools

# import oslo_config.cfg as cfg
import phoenix.config as cfg

from tests.fixture import common

CONF = cfg.CONF


class TestCase(testtools.TestCase):
    """Test case base class for all unit tests."""

    def setUp(self):
        """Run before each test method to initialize test environment."""
        super(TestCase, self).setUp()
        self.useFixture(common.StandardLogging())
        self.useFixture(common.CloudConfigFile(CONF))
