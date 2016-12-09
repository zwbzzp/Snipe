# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# comment
#
# 2016/2/27 fengyc : Init


import os
import sys
import re

# Fix path problem
cur_dir = os.path.abspath(os.path.dirname(__file__))
sys.path.append(cur_dir)

web_dir = os.path.abspath(os.path.join(cur_dir, '..'))
sys.path.append(web_dir)

env_file = os.path.join(cur_dir, '.env')

# Import environment variables
if os.path.exists(env_file):
    print('Importing environment from .env...')
    env = {}
    for line in open(env_file):
        # Skip comments
        if re.match('^\s*#', line):
            continue
        var = line.strip().split('=')
        if len(var) == 2:
            env[var[0]] = var[1]
    os.environ.update(env)

import unittest
from app import app, db
from app.celery_sqlalchemy_scheduler import DatabaseScheduler


class FlaskTest(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.app_context = app.app_context()
        self.app_context.push()
        self.client = self.app.test_client(use_cookies=True)
        #self.app.config['PRESERVE_CONTEXT_ON_EXCEPTION'] = False


    def clear_db_data(self):
        meta = db.metadata
        for table in reversed(meta.sorted_tables):
            db.session.execute(table.delete())
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        self.app_context.pop()


if __name__ != '__main__':
    pass
