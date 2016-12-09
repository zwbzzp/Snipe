# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# Test Config
#
# 2016/9/1 fengyc : Init

import unittest
import os
from phoenix.config import CONF, StrOpt, IntOpt


class ConfigTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        config_file = os.path.join(os.path.dirname(__file__), 'test_config.ini')
        opts = [
            StrOpt('hello', default='Hello', help='Hello string'),
            IntOpt('myint', default=0, help='my int'),
        ]
        CONF.register_opts(opts, 'DEFAULT')
        db_opts = [
            StrOpt('connection', help='Database URL'),
            IntOpt('pool_recycle')
        ]
        CONF.register_opts(db_opts, 'database')
        CONF([config_file])

    def test_str_opt(self):
        self.assertEqual(CONF.DEFAULT.hello, 'Hello')

    def test_int_opt(self):
        self.assertEqual(CONF.DEFAULT.myint, 0)

    def test_db_opts(self):
        self.assertIsNotNone(CONF.database.connection)
        self.assertIsNotNone(CONF.database.pool_recycle)

if __name__ == '__main__':
    unittest.main()
