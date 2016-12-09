# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# comment
#
# 2016/4/21 chengkang : Init

from base import FlaskTest
from flask import url_for
from app.models import User
from app import app
from utils import create_administrator, login_system
from flask.ext.login import current_user

class AuthTest(FlaskTest):

    def setUp(self):
        # this setUp will run once before each test case
        # so in order to reduce the test time, please don't do too much work in setUp
        super(AuthTest, self).setUp()
        # close the wtf csrf
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.client = self.app.test_client()

    ####################################
    # testcase for view "before_request"
    ####################################
    def test_before_request_with_unauthenticated(self):
        # in fact, if a user is unauthenticated, this view will not care about it
        pass

    def test_before_request_with_authenticated_and_unconfirmed(self):
        username, password = "testck", "test123"
        # first, create a user which isn't confirmed
        create_administrator(username, password, confirmed=False)
        # login system with this user
        login_system(self.client, username, password)
        # access the log page
        rv = self.client.post(url_for('log.user_action_logs'))

        # because the user has not confirmed, so redirect to the unconfirmed view
        self.assertTrue(getattr(rv, "_status_code") == 302 and \
                        url_for('auth.unconfirmed') in rv.data.decode('utf-8')) 

    def test_before_request_with_authenticated_and_confirmed(self):
        username, password = "testck", "test123"
        # first, create a user which isn't confirmed
        create_administrator(username, password, confirmed=True)
        # login with the confirmed admin user
        login_system(self.client, username, password)
        # access the log page
        rv = self.client.post(url_for('log.user_action_logs'))

        # will get the log page instead of redirect, so http code is 200
        # the user_action_logs page has the url_for('log.user_action_log_table')
        self.assertTrue(getattr(rv, "_status_code") == 200 and \
                        url_for('log.user_action_log_table') in rv.data.decode('utf-8'))

    #################################
    # testcase for view "unconfirmed"
    #################################
    def test_unconfirmed_with_anonymous(self):
        # access the view
        rv = self.client.get(url_for('auth.unconfirmed'))

        # will redirect to main.index
        self.assertTrue(getattr(rv, "_status_code") == 302 and \
                        url_for('main.index') in rv.data.decode('utf-8'))

    def test_unconfirmed_with_confirmed_user(self):
        username, password = "testck", "test123"
        # first, create a user which isn't confirmed
        create_administrator(username, password, confirmed=True)
        # login with the confirmed admin user
        login_system(self.client, username, password)
        # access the view
        rv = self.client.get(url_for('auth.unconfirmed'))

        # will redirect to main.index
        self.assertTrue(getattr(rv, "_status_code") == 302 and \
                        url_for('main.index') in rv.data.decode('utf-8'))

    def test_unconfirmed_with_unconfirmed_user(self):
        username, password = "testck", "test123"
        # first, create a user which isn't confirmed
        create_administrator(username, password, confirmed=False)
        # login with the confirmed admin user
        login_system(self.client, username, password)
        # access the view
        rv = self.client.get(url_for('auth.unconfirmed'))

        # will get the unconfirmed page
        # fix me, this place can use some representative string to that this is the unconfirmed page
        self.assertTrue(getattr(rv, "status_code") == 200)

    ###########################
    # testcase for view "login"
    ###########################
    def test_login_with_invalid_form(self):
        # access the view with invalid form
        rv = self.client.post(url_for('auth.login'), data=dict())

        # will get the login page
        self.assertTrue(getattr(rv, "_status_code") == 200 and \
                        "username_email" in rv.data.decode('utf-8'))

    def test_login_with_valid_form_and_nonexist_user(self):
        # access the view with valid form, but user nonexist
        rv = self.client.post(url_for('auth.login'), data=dict(username_email="testck", password="test123",
                                                            submit="Log In"))

        # will redirect the login url
        self.assertTrue(getattr(rv, "_status_code") == 302 and \
                        url_for('auth.login') in rv.data.decode('utf-8'))

    def test_login_with_valid_form_and_exist_user(self):
        username, password = "testck", "test123"
        # first, create a user which is confirmed
        create_administrator(username, password, confirmed=True)
        # access the view with valid form, and user exist
        rv = self.client.post(url_for('auth.login'), data=dict(username_email=username, password=password,
                                                            submit="Log In"))

        # will redirect to main.index view
        self.assertTrue(getattr(rv, "_status_code") == 302 and \
                        url_for('main.index') in rv.data.decode('utf-8'))

    ############################
    # testcase for view "logout"
    ############################
    def test_logout_without_login(self):
        # access the view without login first
        rv = self.client.get(url_for('auth.logout'))

        # will redirect to view main.index
        self.assertTrue(getattr(rv, "_status_code") == 302 and \
                        url_for('main.index') in rv.data.decode('utf-8'))

    def test_logout_with_login_first(self):
        username, password = "testck", "test123"
        # first, create a user which is confirmed
        create_administrator(username, password, confirmed=True)
        # login with the confirmed admin user
        login_system(self.client, username, password)

        # access the view
        rv = self.client.get(url_for('auth.logout'))

        # will redirect to view main.index
        self.assertTrue(getattr(rv, "_status_code") == 302 and \
                        url_for('main.index') in rv.data.decode('utf-8'))

    #################################
    # testcase for view "register"
    #################################
    def test_register_with_invalid_form(self):
        # access the view
        rv = self.client.post(url_for('auth.register'), data=dict())

        # will get the register page
        self.assertTrue(getattr(rv, "_status_code") == 200 and \
                        "Register" in rv.data.decode('utf-8'))

    def test_register_with_valid_form(self):
        # access the view
        rv = self.client.post(url_for('auth.register'), data=dict(username="test", email="test@vinzor.com",
                                                                password="test123", password2="test123", submit="Register"))

        # will redirect to login page
        self.assertTrue(getattr(rv, "_status_code") == 302 and \
                        url_for('auth.login') in rv.data.decode('utf-8'))

    def test_register_with_valid_form_and_exist_user(self):
        #in fact, if the username or email is exist, the form will be invalid
        username, password = "test", "test123"
        # first, create a user which is confirmed
        create_administrator(username, password, confirmed=True)

        # access the view
        rv = self.client.post(url_for('auth.register'), data=dict(username=username, email="test@vinzor.com",
                                                                password=password, password2=password, submit="Register"))

        # will get the register page
        self.assertTrue(getattr(rv, "_status_code") == 200 and \
                        "Register" in rv.data.decode('utf-8'))

    #############################
    # testcase for view "confirm"
    #############################
    def test_confirm_with_anonymous(self):
        rv = self.client.get(url_for('auth.confirm', token=123))

        # because of login required, so will redirect to login view
        self.assertTrue(getattr(rv, "_status_code") == 302 and \
                        url_for("auth.login") in rv.data.decode('utf-8'))

    def test_confirm_with_unconfirmed_user_and_invalid_token(self):
        username, password = "testck", "test123"
        # first, create a user which is confirmed
        create_administrator(username, password, confirmed=False)
        # login first
        login_system(self.client, username, password)

        rv = self.client.get(url_for('auth.confirm', token=123))

        #  will redirect to view main.index
        self.assertTrue(getattr(rv, "_status_code") == 302 and \
                        url_for("main.index") in rv.data.decode('utf-8'))

    def test_confirm_with_unconfirmed_user_and_valid_token(self):
        username, password = "testck", "test123"
        # first, create a user which is confirmed
        user = create_administrator(username, password, confirmed=False)
        # login first
        login_system(self.client, username, password)

        # get valid token
        token = user.generate_confirmation_token()

        rv = self.client.get(url_for('auth.confirm', token=token))

        # will redirect to view main.index
        self.assertTrue(getattr(rv, "_status_code") == 302 and \
                        url_for("main.index") in rv.data.decode('utf-8'))

    def test_confirm_with_confirmed_user(self):
        username, password = "testck", "test123"
        # first, create a user which is confirmed
        create_administrator(username, password, confirmed=True)
        # login first
        login_system(self.client, username, password)

        rv = self.client.get(url_for('auth.confirm', token=123))

        # will redirect to view main.index
        self.assertTrue(getattr(rv, "_status_code") == 302 and \
                        url_for("main.index") in rv.data.decode('utf-8'))

    #########################################
    # testcase for view "resend_confirmation"
    #########################################
    def test_resend_confirmation(self):
        username, password = "testck", "test123"
        # first, create a user which is confirmed
        create_administrator(username, password, confirmed=False)
        # login first
        login_system(self.client, username, password)

        rv = self.client.get(url_for('auth.resend_confirmation'))
        # will redirect to view main.index
        self.assertTrue(getattr(rv, "_status_code") == 302 and \
                        url_for("main.index") in rv.data.decode('utf-8'))

    #####################################
    # testcase for view "change_password"
    #####################################
    def test_change_password_with_invalid_form(self):
        username, password = "testck", "test123"
        # first, create a user which is confirmed
        create_administrator(username, password, confirmed=True)
        # login first
        login_system(self.client, username, password)

        rv = self.client.post(url_for('auth.change_password'), data=dict())

        # will get the change_password page
        self.assertTrue(getattr(rv, "_status_code") == 200 and \
                        "Change Password" in rv.data.decode('utf-8'))

    def test_change_password_with_valid_form_and_invalid_old_password(self):
        username, password = "testck", "test123"
        # first, create a user which is confirmed
        create_administrator(username, password, confirmed=True)
        # login first
        login_system(self.client, username, password)

        rv = self.client.post(url_for('auth.change_password'), data=dict(old_password=password + "123",
                                                    password="admin123", password2="admin123", submit="Update Password"))

        self.assertTrue(getattr(rv, "_status_code") == 200 and \
                        "Change Password" in rv.data.decode('utf-8'))

    def test_change_password_with_valid_form_and_valid_old_password(self):
        username, password = "testck", "test123"
        # first, create a user which is confirmed
        user = create_administrator(username, password, confirmed=True)
        # login first
        login_system(self.client, username, password)

        rv = self.client.post(url_for('auth.change_password'), data=dict(old_password=password,
                                                    password="admin123", password2="admin123", submit="Update Password"))

        self.assertTrue(getattr(rv, "_status_code") == 302 and \
                        url_for("main.index") in rv.data.decode('utf-8'))
        self.assertTrue(user.verify_password("admin123"))

    ############################################
    # testcase for view "password_reset_request"
    ############################################
    def  test_password_reset_request_with_nonanonymous(self):
        username, password = "testck", "test123"
        # first, create a user which is confirmed
        create_administrator(username, password, confirmed=True)
        # login first
        login_system(self.client, username, password)

        rv = self.client.post(url_for('auth.password_reset_request'))

        # will redirect to view main.index
        self.assertTrue(getattr(rv, "_status_code") == 302 and \
                        url_for("main.index") in rv.data.decode('utf-8'))

    def test_password_reset_request_with_anonymous_and_invalid_form(self):
        rv = self.client.post(url_for('auth.password_reset_request'), data=dict())

        # will get the reset_password page
        self.assertTrue(getattr(rv, "_status_code") == 200 and \
                        "重置密码" in rv.data.decode('utf-8'))

    def test_password_reset_request_with_anonymous_and_valid_form_but_user_nonexist(self):
        # in fact, when the user nonexist, the form will be invalid
        rv = self.client.post(url_for('auth.password_reset_request'), data=dict(username_email="test", password="test123",
                                                            password2="test123", submit="Reset Password"))

        self.assertTrue(getattr(rv, "_status_code") == 200 and \
                        "重置密码" in rv.data.decode('utf-8'))

    def test_password_reset_request_with_anonymous_and_valid_form_and_user_exist(self):
        username, password = "test", "test123"
        # first, create a user which is confirmed
        user = create_administrator(username, password, confirmed=True)

        rv = self.client.post(url_for('auth.password_reset_request'), data=dict(username_email=username, submit=""))

        # will redirect to login page
        self.assertTrue(getattr(rv, "_status_code") == 302 and \
                        url_for('auth.login') in rv.data.decode('utf-8'))

    ####################################
    # testcase for view "password_reset"
    ####################################
    def test_password_reset_with_nonanonymous(self):
        pass

    ##########################################
    # testcase for view "change_email_request"
    ##########################################


if __name__ == "__main__":
    import unittest
    unittest.main()
