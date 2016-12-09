# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# comment
#
# 2016/4/21 chengkang : Init

from base import FlaskTest
from app.log.utils import UserActionLogger, SystemRunningLogger
from app.models import UserActionLog, User, Role, SystemRunningLog
from flask import url_for, json
import time
from utils import create_administrator, login_system, create_teacher, \
    create_student, logout_system


class LogTest(FlaskTest):
    def setUp(self):
        super(LogTest, self).setUp()
        # close the wtf csrf
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.client = self.app.test_client()
        # create a user action logger and a system running logger
        self.user_action_logger = UserActionLogger()
        self.system_running_logger = SystemRunningLogger()
        # create a administrator to access the web system
        self.username = "admin"
        self.password = "admin123"
        create_administrator(self.username, self.password)
        self.admin = User.query.filter_by(username=self.username).first()

        self.t_username = "teacher"
        self.t_password = "admin123"
        create_teacher(self.t_username, self.t_password)

        self.s_username = "student"
        self.s_password = "admin123"
        create_student(self.s_username, self.s_password)

    def test_empty_db(self):
        user_action_logs = UserActionLog.query.all()
        system_running_logs = SystemRunningLog.query.all()
        self.assertTrue(
            len(user_action_logs) == 0 and len(system_running_logs) == 0)

    def test_ua_log_from_web(self):
        # the view required login
        # when login, will add 1 user action log
        login_system(self.client, self.username, self.password)

        rv = self.client.get(url_for('log.user_action_log_table'))
        json_str = rv.data.decode("utf-8")
        ret_dict = eval(json_str)
        print(ret_dict)

        self.assertTrue(ret_dict.get("iTotalRecords", '-1') == '1' and \
                        ret_dict.get("iTotalDisplayRecords", '-1') == '1')

    def test_sr_log_from_web(self):
        # the view required login
        login_system(self.client, self.username, self.password)

        rv = self.client.get(url_for('log.system_running_log_table'))
        json_str = rv.data.decode("utf-8")
        ret_dict = eval(json_str)

        self.assertTrue(ret_dict.get("iTotalRecords", '-1') == '0' and \
                        ret_dict.get("iTotalDisplayRecords", '-1') == '0')

    def test_user_action_logger(self):
        self.user_action_logger.info(self.admin, "test")

        logs = UserActionLog.query.all()
        self.assertTrue(len(logs) == 1 and logs[0].message == "test" and \
                        logs[0].user is self.admin)

    def test_user_action_log_table(self):
        #########################################
        # path 1        date_range == None && sSortDir == "desc" && sSearch == None && temp_log_list == Null
        #########################################
        date_range = None
        sSortDir = 'desc'
        sSearch = None

        response = self.client.get(
            url_for(
                'log.user_action_log_table') + '?sSortDir_0=' + sSortDir)
        result = response.data.decode('utf-8')
        json_dict = json.loads(response.data)

        self.assertTrue(json_dict.get("iTotalRecords", "") == "0")

        login_system(self.client, self.username, self.password)
        time.sleep(1)
        logout_system(self.client)
        time.sleep(1)
        login_system(self.client, self.username, self.password)

        #########################################
        # path 2        date_range before any log && sSortDir == "desc" && sSearch == None && temp_log_list != Null
        #########################################
        date_range = '11/11/2011 - 11/11/2012'
        sSortDir = 'desc'
        sSearch = None

        response = self.client.get(
            url_for(
                'log.user_action_log_table') + '?sSortDir_0=' + sSortDir + '&date_range=' + date_range)
        result = response.data.decode('utf-8')
        json_dict = json.loads(response.data)

        self.assertTrue(json_dict.get("iTotalRecords", "") == "0")

        # #########################################
        # # path 3        date_range after logs && sSortDir == "desc" && sSearch == None && temp_log_list != Null
        # #########################################
        date_range = '11/11/2021 - 11/11/2022'
        sSortDir = 'desc'
        sSearch = None

        response = self.client.get(
            url_for(
                'log.user_action_log_table') + '?sSortDir_0=' + sSortDir + '&date_range=' + date_range)
        result = response.data.decode('utf-8')
        json_dict = json.loads(response.data)

        self.assertTrue(json_dict.get("iTotalRecords", "") == "0")

        # #########################################
        # # path 4        date_range between logs && sSortDir == "desc" && sSearch == None && temp_log_list != Null
        # #########################################
        date_range = '11/11/2011 - 11/11/2022'
        sSortDir = 'desc'
        sSearch = None

        response = self.client.get(
            url_for(
                'log.user_action_log_table') + '?sSortDir_0=' + sSortDir + '&date_range=' + date_range)
        result = response.data.decode('utf-8')
        # descend
        json_dict = json.loads(response.data)
        self.assertTrue(json_dict.get("iTotalRecords", "") == "3")
        for i in range(2):
            self.assertTrue(json_dict.get('aaData', [])[i][
                                'created_at'] >=
                            json_dict.get('aaData', [])[i + 1][
                                'created_at'])

            # #########################################
            # # path 5        date_range between logs && sSortDir == None && sSearch == None && temp_log_list != Null
            # #########################################
        date_range = '11/11/2011 - 11/11/2022'
        sSortDir = None
        sSearch = None

        response = self.client.get(
            url_for(
                'log.user_action_log_table') + '?date_range=' + date_range)
        result = response.data.decode('utf-8')
        # ascend
        json_dict = json.loads(response.data)

        self.assertTrue(json_dict.get("iTotalRecords", "") == "3")
        for i in range(2):
            self.assertTrue(json_dict.get('aaData', [])[i][
                                'created_at'] <=
                            json_dict.get('aaData', [])[i + 1][
                                'created_at'])

            # #########################################
            # # path 6        date_range between logs && sSortDir == None && sSearch == 'sth else' && temp_log_list != Null
            # #########################################
        date_range = '11/11/2011 - 11/11/2022'
        sSortDir = None
        sSearch = 'sth else'

        response = self.client.get(
            url_for(
                'log.user_action_log_table') + '?date_range=' + date_range + '&sSearch=' + sSearch)
        result = response.data.decode('utf-8')
        # ascend
        json_dict = json.loads(response.data)

        self.assertTrue(json_dict.get("iTotalRecords", "") == "0")

    def test_system_running_logger(self):
        self.system_running_logger.info("test")

        logs = SystemRunningLog.query.all()
        self.assertTrue(len(logs) == 1 and logs[0].message == "test")

    def test_system_running_log_table(self):
        login_system(self.client, self.username, self.password)
        #########################################
        # path 1        date_range == None && sSortDir == "desc" && sSearch == None && temp_log_list == Null
        #########################################
        date_range = None
        sSortDir = 'desc'
        sSearch = None

        response = self.client.get(
            url_for(
                'log.system_running_log_table') + '?sSortDir_0=' + sSortDir)
        result = response.data.decode('utf-8')
        json_dict = json.loads(response.data)

        self.assertTrue(json_dict.get("iTotalRecords", "") == "0")

        self.system_running_logger = SystemRunningLogger()
        self.system_running_logger.info("test1")
        time.sleep(1)
        self.system_running_logger.info("test2")
        time.sleep(1)
        self.system_running_logger.info("test3")
        # #########################################
        # # path 2        date_range before logs && sSortDir == "desc" && sSearch == None && temp_log_list != Null
        # #########################################
        date_range = '11/11/2011 - 11/11/2012'
        sSortDir = 'desc'
        sSearch = None

        response = self.client.get(
            url_for(
                'log.system_running_log_table') + '?date_range=' + date_range + '&sSortDir_0=' + sSortDir)
        result = response.data.decode('utf-8')
        json_dict = json.loads(response.data)

        self.assertTrue(json_dict.get("iTotalRecords", "") == "0")

        # #########################################
        # # path 3        date_range after logs && sSortDir == "desc" && sSearch == None && temp_log_list != Null
        # #########################################
        date_range = '11/11/2021 - 11/11/2022'
        sSortDir = 'desc'
        sSearch = None

        response = self.client.get(
            url_for(
                'log.system_running_log_table') + '?sSortDir_0=' + sSortDir + '&date_range=' + date_range)
        result = response.data.decode('utf-8')
        json_dict = json.loads(response.data)

        self.assertTrue(json_dict.get("iTotalRecords", "") == "0")

        # #########################################
        # # path 4        date_range between logs && sSortDir == "desc" && sSearch == None && temp_log_list != Null
        # #########################################
        date_range = '11/11/2011 - 11/11/2022'
        sSortDir = 'desc'
        sSearch = None

        response = self.client.get(
            url_for(
                'log.system_running_log_table') + '?sSortDir_0=' + sSortDir + '&date_range=' + date_range)
        result = response.data.decode('utf-8')
        # descend
        json_dict = json.loads(response.data)

        self.assertTrue(json_dict.get("iTotalRecords", "") == "3")
        for i in range(2):
            self.assertTrue(json_dict.get('aaData', [])[i][
                                'created_at'] >=
                            json_dict.get('aaData', [])[i + 1][
                                'created_at'])

            # #########################################
            # # path 5        date_range between logs && sSortDir == None && sSearch == None && temp_log_list != Null
            # #########################################
        date_range = '11/11/2011 - 11/11/2022'
        sSortDir = None
        sSearch = None

        response = self.client.get(
            url_for(
                'log.system_running_log_table') + '?date_range=' + date_range)
        result = response.data.decode('utf-8')
        # ascend
        json_dict = json.loads(response.data)

        self.assertTrue(json_dict.get("iTotalRecords", "") == "3")
        for i in range(2):
            self.assertTrue(json_dict.get('aaData', [])[i][
                                'created_at'] <=
                            json_dict.get('aaData', [])[i + 1][
                                'created_at'])

            # #########################################
            # # path 6        date_range between logs && sSortDir == None && sSearch == 'sth else' && temp_log_list != Null
            # #########################################
        date_range = '11/11/2011 - 11/11/2022'
        sSortDir = None
        sSearch = 'sth else'

        response = self.client.get(
            url_for(
                'log.system_running_log_table') + '?date_range=' + date_range + '&sSearch=' + sSearch)
        result = response.data.decode('utf-8')
        json_dict = json.loads(response.data)

        self.assertTrue(json_dict.get("iTotalRecords", "") == "0")

    def tearDown(self):
        UserActionLog.query.delete()
        User.query.delete()
        Role.query.delete()
        SystemRunningLog.query.delete()
        super(LogTest, self).tearDown()

if __name__ == "__main__":
    import unittest
    unittest.main()

