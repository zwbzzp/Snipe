# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# comment
#
# 2016/8/31 luzh : Init

from base import FlaskTest
from utils import create_administrator, login_system, create_teacher, \
    create_student

from app.models import User, Desktop, Parameter, DesktopType, \
    DesktopTask, Course,Lesson, Period
from flask import url_for, json
import time
from app import db
import datetime
import os

from flask import jsonify

web_dir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
resource_dir = os.path.join(web_dir, 'resources')


class EduTest(FlaskTest):
    def setUp(self):
        super(EduTest, self).setUp()
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.client = self.app.test_client()

        # create a administrator to access the web system
        self.username = "admin"
        self.password = "admin123"
        create_administrator(self.username, self.password)

        self.t_username = "teacher"
        self.t_password = "admin123"
        create_teacher(self.t_username, self.t_password)

        self.s_username = "student1"
        self.s_password = "admin123"
        create_student(self.s_username, self.s_password)

        self.s1_username = "student2"
        self.s1_password = "admin123"
        create_student(self.s1_username, self.s1_password)

        course_name = "测试课程"
        self.create_course(course_name,self.username)
        self.course_id = Course.query.filter_by(name=course_name).first().id

    def tearDown(self):
        Course.query.delete()
        Desktop.query.delete()
        Lesson.query.delete()
        db.session.commit()
        super(EduTest, self).tearDown()


    def test_get_timetable(self):
        login_system(self.client, self.username, self.password)
        course = Course.query.filter_by(id=self.course_id).first()
        start_date = '2016-08-20'
        response = self.client.post(url_for('edu.get_timetable', id=course.id), data=dict(week_start_date=start_date))
        assert response.status_code == 200

    def test_update_course_info(self):
        login_system(self.client, self.username, self.password)

        course = Course.query.filter_by(id=self.course_id).first()

        # 更新课程信息
        name = "测试课程11"
        start_date = datetime.datetime.strptime("2016-09-01", '%Y-%m-%d').date()
        end_date = datetime.datetime.strptime("2016-09-30", '%Y-%m-%d').date()
        capacity = 2
        image_ref = "dfc73db0-ed5c-4c82-938b-9e7be24f6f8a"
        flavor_ref = "40b2599d-01ac-48b2-875b-0c1e69638bed"
        network_ref = "36286445-2324-4ee1-bee9-9a914c23a921"
        owner_id = 1
        protocol = 2
        response = self.client.post(url_for('edu.update_course', id=course.id),
                                    data=dict(name=name, start_date=start_date, end_date=end_date,
                                              capacity=capacity,
                                              image_ref=image_ref, flavor_ref=flavor_ref, network_ref=network_ref,
                                              owner_id=owner_id, protocol=protocol))

        response = self.client.get(url_for("edu.course_detail", id=course.id))
        self.assertTrue("测试课程11" in response.get_data(as_text=True))

    def test_update_course_student(self):
        login_system(self.client, self.username, self.password)

        course = Course.query.filter_by(id=self.course_id).first()
        students = "2,5"
        response = self.client.post(url_for('edu.update_course', id=course.id),
                                    data=dict(students=students))
        response = self.client.get(url_for("edu.course_detail", id=course.id))
        print(response.get_data(as_text=True))
        self.assertTrue("学生haha添加成功" in response.get_data(as_text=True))
        self.assertTrue("学生student添加成功" in response.get_data(as_text=True))

    def test_update_course_student_conflict(self):
        login_system(self.client, self.username, self.password)

        course = Course.query.filter_by(id=self.course_id).first()
        student1= User.query.filter_by(username="student1").first().id
        student2 = User.query.filter_by(username="student2").first().id
        students = str(student1) + "," + str(student2)
        response = self.client.post(url_for('edu.update_course', id=course.id),
                                    data=dict(students=students))
        students = str(student1)
        response = self.client.post(url_for('edu.update_course', id=course.id),
                                    data=dict(students=students))
        response = self.client.get(url_for("edu.course_detail", id=course.id))
        print(response.get_data(as_text=True))
        self.assertTrue("学生student1已经存在于名单中，添加失败" in response.get_data(as_text=True))


    def test_add_save_timetable(self):
        login_system(self.client, self.username, self.password)
        course = Course.query.filter_by(id=self.course_id).first()

        change_lessons = {'add_lessons_lists':{'2016-08-29':{'3_4':'3_4'}},
                          'delete_lessons_lists':{'2016-08-29':{}}}
        response = self.client.post(url_for('edu.save_timetable', id=course.id),
                                    data = json.dumps(change_lessons), content_type = 'application/json')
        response = self.client.get(url_for("edu.course_detail", id=course.id))
        self.assertTrue("添加时间段 2016-09-02 %s ~ 2016-09-02 %s" % ((Period.query.filter_by(name=3).first().start_time).strftime('%H:%M'),
                          (Period.query.filter_by(name=3).first().end_time).strftime('%H:%M')) in response.get_data(as_text=True))

    def test_add_save_timetable_conflict(self):
        login_system(self.client, self.username, self.password)
        course = Course.query.filter_by(id=self.course_id).first()

        change_lessons = {'add_lessons_lists': {'2016-08-29': {'3_4': '3_4'}},
                          'delete_lessons_lists': {'2016-08-29': {}}}
        response = self.client.post(url_for('edu.save_timetable', id=course.id),
                                    data=json.dumps(change_lessons), content_type='application/json')
        change_lessons = {'add_lessons_lists': {'2016-08-29': {'3_4': '3_4'}},
                          'delete_lessons_lists': {'2016-08-29': {}}}

        response = self.client.post(url_for('edu.save_timetable', id=course.id),
                                    data=json.dumps(change_lessons), content_type='application/json')
        response = self.client.get(url_for("edu.course_detail", id=course.id))
        self.assertTrue("时间段冲突 2016-09-02 %s ~ 2016-09-02 %s" % ((Period.query.filter_by(name=3).first().start_time).strftime('%H:%M'),
                                                                 (Period.query.filter_by(name=3).first().end_time).strftime('%H:%M')) in response.get_data(as_text=True))

    def test_add_save_timetable_overdate(self):
        login_system(self.client, self.username, self.password)
        course = Course.query.filter_by(id=self.course_id).first()

        change_lessons = {'add_lessons_lists': {'2016-07-25': {'3_4': '3_4'}},
                          'delete_lessons_lists': {'2016-07-25': {}}}
        response = self.client.post(url_for('edu.save_timetable', id=course.id),
                                    data=json.dumps(change_lessons), content_type='application/json')
        response = self.client.get(url_for("edu.course_detail", id=course.id))
        print(response.get_data(as_text=True))
        self.assertTrue("时间段超出课程时间限制 2016-07-29 %s ~ 2016-07-29 %s" % (
                        (Period.query.filter_by(name=3).first().start_time).strftime('%H:%M'),
                        (Period.query.filter_by(name=3).first().end_time).strftime('%H:%M')) in response.get_data(as_text=True))

    def test_delete_save_timetable(self):
        login_system(self.client, self.username, self.password)
        course = Course.query.filter_by(id=self.course_id).first()

        change_lessons = {'add_lessons_lists': {'2016-08-29': {'3_4': '3_4','4_4': '4_4'}},
                          'delete_lessons_lists': {'2016-08-29': {'3_4': '3_4'}}}
        response = self.client.post(url_for('edu.save_timetable', id=course.id),
                                    data=json.dumps(change_lessons), content_type='application/json')
        response = self.client.get(url_for("edu.course_detail", id=course.id))
        self.assertTrue("上课时段 2016-09-02 %s ~ 2016-09-02 %s 删除成功" % ((Period.query.filter_by(name=3).first().start_time).strftime('%H:%M'),
                                                                 (Period.query.filter_by(name=3).first().end_time).strftime('%H:%M')) in response.get_data(as_text=True))

    @staticmethod
    def create_course(coursename, ownername):
        """
        create
        :param: coursename
        :return:
        """
        course = Course(name=coursename)
        course.start_date = datetime.datetime.strptime("2016-08-01", '%Y-%m-%d').date()
        course.end_date = datetime.datetime.strptime("2016-09-30", '%Y-%m-%d').date()
        course.capacity = 4
        course.image_ref = os.environ.get('OS_IMAGE_REF')  # cirros-x86
        course.flavor_ref = "f4cb92aa-65f4-450b-a7ed-50c85f5bfc68"  # m1.tiny
        course.network_ref = "36286445-2324-4ee1-bee9-9a914c23a921"
        course.owner = User.query.filter_by(username=ownername).first()
        db.session.add(course)
        db.session.commit()
        return course