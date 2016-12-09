# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# fixtures
#
# 20160113 lipeizhao : Init

import os
import fixtures
import logging as std_logging
# from oslo_config import fixture as config_fixture
from flask import current_app
from phoenix.app import create_app, db
from phoenix.config import CONF


class StandardLogging(fixtures.Fixture):
    """
    Setup Logging redirection for tests.
    """

    def _setUp(self):
        # set root logger to debug
        root = std_logging.getLogger()
        root.setLevel(std_logging.DEBUG)

        # Collect logs
        fs = '%(asctime)s %(levelname)s [%(name)s] %(message)s'
        self.logger = self.useFixture(fixtures.FakeLogger(format=fs, level=None))


class CloudConfigFile(fixtures.Fixture):
    """
    Setup config environment using default config file
    """

    def _setUp(self):
        local_dir = os.path.abspath(os.path.dirname(__file__))
        src_dir = os.path.abspath(os.path.join(local_dir, '..', '..'))
        conf_file = os.path.abspath(os.path.join(src_dir, 'etc/phoenix.ini'))
        # self.conf(default_config_files=[conf_dir], args=None)
        CONF([conf_file])
        self.addCleanup(self._cleanUp)

    def _cleanUp(self):
        CONF.clear()
