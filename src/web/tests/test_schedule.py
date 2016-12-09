# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# comment
#
# 2016/5/25 huangyongjie : Init

from base import FlaskTest
from utils import create_administrator, login_system
from app.models import DesktopTask
from flask import url_for, json
from app import db


class ScheduleTest(FlaskTest):
    def setUp(self):
        super(ScheduleTest, self).setUp()
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.client = self.app.test_client()

        # create a administrator to access the web system
        self.username = "admin"
        self.password = "admin123"
        create_administrator(self.username, self.password)

    def test_task_detail(self):
        login_system(self.client, self.username, self.password)
#########################################
# path 1        task != None
#########################################
        task = DesktopTask()
        db.session.add(task)
        db.session.commit()
        response = self.client.get(url_for('schedule.task_detail', id=task.id))
        result = response.data.decode('utf-8')
        self.assertEqual(response.status_code, 200)

#########################################
# path 2        task == None
#########################################
        response = self.client.get(url_for('schedule.task_detail', id=333))
        result = response.data.decode('utf-8')
        self.assertEqual(response.status_code, 404)

    def test_delete_task(self):
        login_system(self.client, self.username, self.password)
#########################################
# path 1        tasks == Null
#########################################
        tasks = []
        response = self.client.delete(url_for('schedule.delete_task'), data=json.dumps(
            tasks), content_type='application/json')
        result = response.data.decode('utf-8')
        json_dict = json.loads(response.data)
        self.assertTrue(json_dict.get("status", "") == "success")

        json_dict_data = json_dict.get("data", {})
        self.assertTrue(len(json_dict_data.get("success_list", [])) == 0)
        self.assertTrue(len(json_dict_data.get("fail_list", [])) == 0)

#########################################
# path 2        tasks != Null  && query nothing in db
#########################################
        tasks = [333]
        response = self.client.delete(url_for('schedule.delete_task'), data=json.dumps(
            tasks), content_type='application/json')
        result = response.data.decode('utf-8')
        json_dict = json.loads(response.data)
        self.assertTrue(json_dict.get("status", "") == "success")

        json_dict_data = json_dict.get("data", {})
        self.assertTrue(len(json_dict_data.get("success_list", [])) == 0)
        self.assertTrue(len(json_dict_data.get("fail_list", [])) == 1)

#########################################
# path 3        tasks != Null  && query sth in db
#########################################
        task = DesktopTask()
        db.session.add(task)
        db.session.commit()
        tasks = [task.id]
        response = self.client.delete(url_for('schedule.delete_task'), data=json.dumps(
            tasks), content_type='application/json')
        result = response.data.decode('utf-8')
        json_dict = json.loads(response.data)
        self.assertTrue(json_dict.get("status", "") == "success")

        json_dict_data = json_dict.get("data", {})
        self.assertTrue(len(json_dict_data.get("success_list", [])) == 1)
        self.assertTrue(len(json_dict_data.get("fail_list", [])) == 0)

    def test_tasks_action(self):
        login_system(self.client, self.username, self.password)
#########################################
# path 1        tasks == Null
#########################################
        tasks = []
        response = self.client.put(url_for('schedule.tasks_action', action='asd'), data=json.dumps(
            tasks), content_type='application/json')
        result = response.data.decode('utf-8')
        json_dict = json.loads(response.data)
        self.assertTrue(json_dict.get("status", "") == "success")

        json_dict_data = json_dict.get("data", {})
        self.assertTrue(len(json_dict_data.get("success_list", [])) == 0)
        self.assertTrue(len(json_dict_data.get("fail_list", [])) == 0)

#########################################
# path 2        tasks != Null && task != None && action == "resume"
#########################################
        task = DesktopTask()
        task.stage_chain = json.dumps(['BUILD', 'WAIT', 'FLOATING', 'DETECT'])
        db.session.add(task)
        db.session.commit()
        tasks = [task.id]
        response = self.client.put(url_for('schedule.tasks_action', action='resume'), data=json.dumps(
            tasks), content_type='application/json')
        result = response.data.decode('utf-8')
        json_dict = json.loads(response.data)
        self.assertTrue(json_dict.get("status", "") == "success")

        json_dict_data = json_dict.get("data", {})
        self.assertTrue(len(json_dict_data.get("success_list", [])) == 1)
        self.assertTrue(len(json_dict_data.get("fail_list", [])) == 0)

#########################################
# path 3        tasks != Null && task != None && action == "reset"
#########################################
        task = DesktopTask()
        task.stage_chain = json.dumps(['BUILD', 'WAIT', 'FLOATING', 'DETECT'])
        db.session.add(task)
        db.session.commit()
        tasks = [task.id]
        response = self.client.put(url_for('schedule.tasks_action', action='reset'), data=json.dumps(
            tasks), content_type='application/json')
        result = response.data.decode('utf-8')
        json_dict = json.loads(response.data)
        self.assertTrue(json_dict.get("status", "") == "success")

        json_dict_data = json_dict.get("data", {})
        self.assertTrue(len(json_dict_data.get("success_list", [])) == 1)
        self.assertTrue(len(json_dict_data.get("fail_list", [])) == 0)

#########################################
# path 4        tasks != Null && task != None && action == "disable"
#########################################
        task = DesktopTask()
        task.stage_chain = json.dumps(['BUILD', 'WAIT', 'FLOATING', 'DETECT'])
        db.session.add(task)
        db.session.commit()
        tasks = [task.id]
        response = self.client.put(url_for('schedule.tasks_action', action='disable'), data=json.dumps(
            tasks), content_type='application/json')
        result = response.data.decode('utf-8')
        json_dict = json.loads(response.data)
        self.assertTrue(json_dict.get("status", "") == "success")

        json_dict_data = json_dict.get("data", {})
        self.assertTrue(len(json_dict_data.get("success_list", [])) == 1)
        self.assertTrue(len(json_dict_data.get("fail_list", [])) == 0)

#########################################
# path 5        tasks != Null && task != None && action == "enable"
#########################################
        task = DesktopTask()
        task.stage_chain = json.dumps(['BUILD', 'WAIT', 'FLOATING', 'DETECT'])
        db.session.add(task)
        db.session.commit()
        tasks = [task.id]
        response = self.client.put(url_for('schedule.tasks_action', action='enable'), data=json.dumps(
            tasks), content_type='application/json')
        result = response.data.decode('utf-8')
        json_dict = json.loads(response.data)
        self.assertTrue(json_dict.get("status", "") == "success")

        json_dict_data = json_dict.get("data", {})
        self.assertTrue(len(json_dict_data.get("success_list", [])) == 1)
        self.assertTrue(len(json_dict_data.get("fail_list", [])) == 0)

#########################################
# path 6        tasks != Null && task != None && (action not in action_list
#########################################
        task = DesktopTask()
        task.stage_chain = json.dumps(['BUILD', 'WAIT', 'FLOATING', 'DETECT'])
        db.session.add(task)
        db.session.commit()
        tasks = [task.id]
        response = self.client.put(url_for('schedule.tasks_action', action='ABC'), data=json.dumps(
            tasks), content_type='application/json')
        result = response.data.decode('utf-8')
        json_dict = json.loads(response.data)
        self.assertTrue(json_dict.get("status", "") == "success")

        json_dict_data = json_dict.get("data", {})
        self.assertTrue(len(json_dict_data.get("success_list", [])) == 1)
        self.assertTrue(len(json_dict_data.get("fail_list", [])) == 0)

#########################################
# path 7        tasks != Null && task == None
#########################################
        tasks = [343]
        response = self.client.put(url_for('schedule.tasks_action', action='ABC'), data=json.dumps(
            tasks), content_type='application/json')
        result = response.data.decode('utf-8')
        json_dict = json.loads(response.data)
        self.assertTrue(json_dict.get("status", "") == "success")

        json_dict_data = json_dict.get("data", {})
        self.assertTrue(len(json_dict_data.get("success_list", [])) == 0)
        self.assertTrue(len(json_dict_data.get("fail_list", [])) == 1)

    def test_task_table(self):
        login_system(self.client, self.username, self.password)
#########################################
# path 1        iSortCol_0_0 ! = None && sSortDir_0 == "desc" && sSearch == None && task_list == Null
#########################################
        sSortDir_0 = 'desc'
        iSortCol_0 = '0'
        sSearch = None
        response = self.client.get(url_for(
            'schedule.task_table') + '?sEcho=sEcho&iDisplayStart=0&iDisplayLength=25&sSortDir_0=' + sSortDir_0 + '&iSortCol_0_0=' + iSortCol_0)
        result = response.data.decode('utf-8')
        json_dict = json.loads(response.data)

        self.assertTrue(len(json_dict.get("aaData", [])) == 0)

#########################################
# path 2        iSortCol_0_0 == None && sSortDir_0 == None && sSearch == None && task_list != Null
#########################################
        sSearch = None
        sSortDir_0 = None
        iSortCol_0 = None
        task = DesktopTask()
        task.stage_chain = json.dumps(['BUILD', 'WAIT', 'FLOATING', 'DETECT'])
        db.session.add(task)
        db.session.commit()
        response = self.client.get(url_for(
            'schedule.task_table') + '?sEcho=sEcho&iDisplayStart=0&iDisplayLength=25')
        result = response.data.decode('utf-8')
        json_dict = json.loads(response.data)

        self.assertTrue(len(json_dict.get("aaData", [])) > 0)

#########################################
# path 3        iSortCol_0 != None && sSortDir_0 == "desc" && sSearch == None && task_list != Null
#########################################
        sSortDir_0 = "desc"
        sSearch = None
        iSortCol_0 = '0'
        task = DesktopTask()
        task.stage_chain = json.dumps(['BUILD', 'WAIT', 'FLOATING', 'DETECT'])
        db.session.add(task)
        db.session.commit()
        response = self.client.get(url_for(
            'schedule.task_table') + '?sEcho=sEcho&iDisplayStart=0&iDisplayLength=25&sSortDir_0=' + sSortDir_0 + '&iSortCol_0=' + iSortCol_0)
        result = response.data.decode('utf-8')
        json_dict = json.loads(response.data)

        self.assertTrue(len(json_dict.get("aaData", [])) > 0)

#########################################
# path 4        iSortCol_0 != None && sSortDir_0 == "desc" && (sSearch != None && sSearch != \'')  task_list != Null
#########################################
        sSortDir_0 = 'desc'
        sSearch = 'nothing'
        iSortCol_0 = '0'
        task = DesktopTask()
        task.stage_chain = json.dumps(['BUILD', 'WAIT', 'FLOATING', 'DETECT'])
        db.session.add(task)
        db.session.commit()
        response = self.client.get(url_for(
            'schedule.task_table') + '?sEcho=sEcho&iDisplayStart=0&iDisplayLength=25&sSortDir_0=' + sSortDir_0 + '&iSortCol_0=' + iSortCol_0 + '&sSearch=' + sSearch)
        result = response.data.decode('utf-8')
        json_dict = json.loads(response.data)

        self.assertTrue(len(json_dict.get("aaData", [])) == 0)

#########################################
# path 5        iSortCol_0 != None && sSortDir_0 == "desc" && sSearch == None && task_list != Null
#########################################
        sSortDir_0 = 'desc'
        iSortCol_0 = '0'
        sSearch = None
        task = DesktopTask()
        task.stage_chain = json.dumps(['BUILD', 'WAIT', 'FLOATING', 'DETECT'])
        db.session.add(task)
        db.session.commit()
        response = self.client.get(url_for(
            'schedule.task_table') + '?sEcho=sEcho&iDisplayStart=0&iDisplayLength=25&sSortDir_0=' + sSortDir_0 + '&iSortCol_0=' + iSortCol_0)
        result = response.data.decode('utf-8')
        json_dict = json.loads(response.data)

        self.assertTrue(len(json_dict.get("aaData", [])) > 0)

    def tearDown(self):
        DesktopTask.query.delete()
        db.session.commit()
        super(ScheduleTest, self).tearDown()
