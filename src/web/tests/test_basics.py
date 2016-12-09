# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# comment
#
# 2016/2/26 fengyc : Init

from flask import current_app
from base import FlaskTest
from utils import create_administrator, create_teacher, create_student, \
    create_course
from app.models import User
from app import db

class BasicsTestCase(FlaskTest):

    def setUp(self):
        super(BasicsTestCase, self).setUp()
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.username = "admin"
        self.password = "admin123"
        self.client = self.app.test_client()
        create_administrator(self.username, self.password)

    def test_app_exists(self):
        self.assertIsNotNone(current_app)

    def test_app_is_testing(self):
        self.assertTrue(current_app.config['TESTING'])

    def test_database(self):
        studentname = "zhuwenbiao"
        password = "admin123"
        create_student(studentname, password)

        teachername = "wenwushao"
        password = "admin123"
        create_teacher(teachername, password)

        assert User.query.all() is not None

    def tearDown(self):
        User.query.delete()
        db.session.commit()
        super(BasicsTestCase, self).tearDown()

