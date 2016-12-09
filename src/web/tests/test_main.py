# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# comment
#
# 2016/5/21 huangyongjie : Init

import datetime
from base import FlaskTest
from utils import create_administrator, login_system
from flask import url_for, json
from babel import dates


class MainTest(FlaskTest):
    def setUp(self):
        super(MainTest, self).setUp()
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.client = self.app.test_client()

        # create a administrator to access the web system
        self.username = "admin"
        self.password = "admin123"
        create_administrator(self.username, self.password)

    def test_index(self):
        # login_required
        login_system(self.client, self.username, self.password)
        response = self.client.get(url_for('main.index'))
        result = response.data.decode('utf-8')
        self.assertEqual(response.status_code, 200)

#########################################
# path 1        start_date != None
#########################################
        start_date = '2016-5-16'
        response = self.client.get(
            (url_for('main.index') + '?start_date=' + start_date))
        result = response.data.decode('utf-8')
        date = datetime.datetime.strptime(
            start_date, '%Y-%m-%d').date()
        weekday = date.weekday()
        start_date = date - datetime.timedelta(days=weekday)
        expected_date = dates.format_date(start_date, 'yyyy年MM月dd日')

        self.assertTrue(expected_date in result)
        self.assertEqual(response.status_code, 200)

#########################################
# path 2        start_date == None
#########################################
        response = self.client.get(url_for('main.index'))
        result = response.data.decode('utf-8')
        date = datetime.date.today()
        weekday = date.weekday()
        start_date = date - datetime.timedelta(days=weekday)
        expected_date = dates.format_date(start_date, 'yyyy年MM月dd日')

        self.assertTrue(expected_date in result)
        self.assertEqual(response.status_code, 200)

    def tearDown(self):
        super(MainTest, self).tearDown()
