# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# Test base
#
# 2016/1/22 fengyc : Init

import unittest
import os

from phoenix.config import CONF

# Setup oslo_config
TESTDIR = os.path.abspath(os.path.pardir(__file__))
SRCROOT = os.path.abspath(os.path.pardir(TESTDIR))
ETCDIR = os.path.abspath(os.path.join(SRCROOT, 'etc'))
CONFFILE = os.path.abspath(os.path.join(ETCDIR, 'phoenix-test.ini'))
CONF(default_config_files=[CONFFILE])

# Setup logging

class TestBase(unittest.TestCase):
    def setUpClass(cls):
        pass