# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# comment
#
# 2016/4/21 chengkang : Init

from base import FlaskTest
from flask import url_for, json
from app.models import User, Role, Permission
from app import app, db
from utils import create_administrator, create_teacher, create_student, login_system
import uuid
import pyexcel.ext.xls as xls
import io

class AccountTest(FlaskTest):

    def setUp(self):
        # this setUp will run once before each test case
        # so in order to reduce the test time, please don't do too much work in setUp
        super(AccountTest, self).setUp()
        # close the wtf csrf
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.client = self.app.test_client()

        # create default roles
        self.create_role("Administrator", des="Administrator")
        self.create_role("Teacher", permissions=(Permission.COURSE | Permission.DESKTOP), des="Teacher")
        self.create_role("Student", permissions=(Permission.DESKTOP), des="Student")


    def login_first_with_admin(self, username=None):
        # this function is used for solve login_required and rights issue
        username, password = username if username else str(uuid.uuid4())[:20], str(uuid.uuid4())[:20]
        # first, create a user which isn't confirmed
        admin = create_administrator(username, password, confirmed=True)
        # login system with this user
        login_system(self.client, username, password)
        return admin

    def login_first_with_teacher(self, username=None):
        username, password = username if username else str(uuid.uuid4())[
                                                       :20], str(uuid.uuid4())[
                                                             :20]
        teacher = create_teacher(username, password, confirmed=True)
        login_system(self.client, username, password)
        return teacher

    def login_first_with_student(self, username=None):
        username, password = username if username else str(uuid.uuid4())[
                                                       :20], str(uuid.uuid4())[
                                                             :20]
        student = create_student(username, password, confirmed=True)
        login_system(self.client, username, password)
        return student


    def create_role(self, name, permissions=0x80, des="test"):
        role = Role.query.filter_by(name=name).first()
        if role is None:
            role = Role(name=name, permissions=permissions, description=des)
            db.session.add(role)
            db.session.commit()
        return role

    ####################################
    # testcase for view "users"
    ####################################
    def test_users_with_unexist_role(self):
        self.login_first_with_admin()

        rv = self.client.get(url_for('account.users', role_name="test"))

        # 404
        self.assertTrue(getattr(rv, "status_code") == 404)
        
    def test_users_with_exist_role(self):
        # admin.html
        admin = self.login_first_with_admin()
        rv = self.client.get(url_for('account.users', role_name=admin.role.name))
        self.assertTrue(getattr(rv, "status_code") == 200)
        html = rv.data.decode('utf-8')
        self.assertTrue('管理员' in html)

        # teacher.html
        rv = self.client.get(
            url_for('account.users', role_name='Teacher'))
        self.assertTrue(getattr(rv, "status_code") == 200)
        html = rv.data.decode('utf-8')
        self.assertTrue('教师管理' in html)

        # student.html
        rv = self.client.get(
            url_for('account.users', role_name='Student'))
        self.assertTrue(getattr(rv, "status_code") == 200)
        html = rv.data.decode('utf-8')
        self.assertTrue('学生管理' in html)

    def test_users_with_no_permission(self):
        student = self.login_first_with_student()

        rv = self.client.get(
            url_for('account.users', role_name='Administrator'))
        self.assertTrue(getattr(rv, "status_code") == 403)

        rv = self.client.get(
            url_for('account.users', role_name='Teacher'))
        self.assertTrue(getattr(rv, "status_code") == 403)

        rv = self.client.get(
            url_for('account.users', role_name='Student'))
        self.assertTrue(getattr(rv, "status_code") == 403)


    ####################################
    # testcase for view "create_user"
    ####################################
    def test_create_user_with_invalid_form(self):
        self.login_first_with_admin()

        rv = self.client.post(url_for('account.create_user'), data=dict())
        self.assertTrue(getattr(rv, "status_code") == 200)
        json_dict = json.loads(rv.data)
        self.assertTrue(json_dict.get('status', '') == 'fail')

    def test_create_user_with_valid_form_but_user_exist(self):
        # in fact, when the username or user exist, the form is invalid
        admin = self.login_first_with_admin()

        role = self.create_role("test")
        fullname = "test"
        rv = self.client.post(url_for('account.create_user'),
                              data=dict(fullname=fullname,
                                        username=admin.username, role=role.name,
                                        email="test@vinzor.com",
                                        password="test123", confirm="test123"))
        json_dict = json.loads(rv.data)

        self.assertTrue(json_dict.get('status', '') == 'fail')
        self.assertFalse(User.query.filter_by(fullname=fullname).first())

    def test_create_user_with_valid_form(self):
        admin = self.login_first_with_admin()

        # create administrator
        fullname, username = "test", "test"
        rv = self.client.post(url_for('account.create_user'), data=dict(fullname=fullname, username=username, role=admin.role.name,
                                                            email="test@vinzor.com", password="test123", confirm="test123"))
        print(rv.data)
        json_dict = json.loads(rv.data)
        self.assertTrue(json_dict.get('status', '') == 'success')
        new_user = User.query.filter_by(username=username).first()
        self.assertTrue(new_user)
        db.session.delete(new_user)
        db.session.commit()

        # create teacher
        rv = self.client.post(url_for('account.create_user'),
                              data=dict(fullname=fullname, username=username,
                                        role='Teacher',
                                        email="test@vinzor.com",
                                        password="test123", confirm="test123"))
        print(rv.data)
        json_dict = json.loads(rv.data)
        self.assertTrue(json_dict.get('status', '') == 'success')
        new_user = User.query.filter_by(username=username).first()
        self.assertTrue(new_user)
        db.session.delete(new_user)
        db.session.commit()

        # create student
        rv = self.client.post(url_for('account.create_user'),
                              data=dict(fullname=fullname, username=username,
                                        role='Student',
                                        email="test@vinzor.com",
                                        password="test123", confirm="test123"))
        print(rv.data)
        json_dict = json.loads(rv.data)
        self.assertTrue(json_dict.get('status', '') == 'success')
        new_user = User.query.filter_by(username=username).first()
        self.assertTrue(new_user)
        db.session.delete(new_user)
        db.session.commit()


    def test_create_user_without_permission(self):
        student = self.login_first_with_student()

        # create administrator
        fullname, username = "test", "test"
        rv = self.client.post(url_for('account.create_user'),
                              data=dict(fullname=fullname, username=username,
                                        role='Administrator',
                                        email="test@vinzor.com",
                                        password="test123", confirm="test123"))
        self.assertTrue(getattr(rv, "status_code") == 403)

        # create teacher
        fullname, username = "test", "test"
        rv = self.client.post(url_for('account.create_user'),
                              data=dict(fullname=fullname, username=username,
                                        role='Teacher',
                                        email="test@vinzor.com",
                                        password="test123", confirm="test123"))
        self.assertTrue(getattr(rv, "status_code") == 403)

        # create student
        fullname, username = "test", "test"
        rv = self.client.post(url_for('account.create_user'),
                              data=dict(fullname=fullname, username=username,
                                        role='Student',
                                        email="test@vinzor.com",
                                        password="test123", confirm="test123"))
        self.assertTrue(getattr(rv, "status_code") == 403)


    ####################################
    # testcase for view "delete_users"
    ####################################
    def test_delete_users_with_empty_list(self):
        self.login_first_with_admin()

        rv = self.client.delete(url_for('account.delete_users'), data=json.dumps(list()), content_type = 'application/json')

        self.assertTrue(getattr(rv, "status_code") == 200)

        json_dict = json.loads(rv.data)
        self.assertTrue(json_dict.get("status", "") == "success")

        json_dict_data = json_dict.get("data", {})
        self.assertFalse(json_dict_data.get("success_list"))
        self.assertFalse(json_dict_data.get("fail_list"))

    def test_delete_users_with_one_nonexist_user(self):
        admin = self.login_first_with_admin()

        # the data is a list contains user's id, it can be str or int
        rv = self.client.delete(url_for('account.delete_users'), data=json.dumps([admin.id+1]), content_type = 'application/json')

        self.assertTrue(getattr(rv, "status_code") == 200)

        json_dict = json.loads(rv.data)
        self.assertTrue(json_dict.get("status", "") == "success")

        json_dict_data = json_dict.get("data", {})
        self.assertFalse(json_dict_data.get("success_list"))
        self.assertTrue(len(json_dict_data.get("fail_list", [])) == 1)

    def test_delete_users_with_one_exist_user(self):
        admin = self.login_first_with_admin()

        rv = self.client.delete(url_for('account.delete_users'), data=json.dumps([admin.id]), content_type = 'application/json')

        self.assertTrue(getattr(rv, "status_code") == 200)

        json_dict = json.loads(rv.data)
        self.assertTrue(json_dict.get("status", "") == "success")

        json_dict_data = json_dict.get("data", {})
        self.assertFalse(json_dict_data.get("fail_list"))
        self.assertTrue(len(json_dict_data.get("success_list", [])) == 1)

    def test_delete_users_with_one_exist_user_and_one_nonexist_user(self):
        admin = self.login_first_with_admin()

        rv = self.client.delete(url_for('account.delete_users'), data=json.dumps([admin.id, admin.id+1]), content_type = 'application/json')

        self.assertTrue(getattr(rv, "status_code") == 200)

        json_dict = json.loads(rv.data)
        self.assertTrue(json_dict.get("status", "") == "success")

        json_dict_data = json_dict.get("data", {})
        self.assertTrue(len(json_dict_data.get("success_list", [])) == 1)
        self.assertTrue(len(json_dict_data.get("fail_list", [])) == 1)

    def test_delete_users_with_one_super_administrator(self):
        super_admin = self.login_first_with_admin('admin')

        rv = self.client.delete(url_for('account.delete_users'),
                                data=json.dumps([super_admin.id]),
                                content_type='application/json')

        self.assertTrue(getattr(rv, "status_code") == 200)

        json_dict = json.loads(rv.data)
        self.assertTrue(json_dict.get("status", "") == "success")

        json_dict_data = json_dict.get("data", {})
        self.assertTrue(len(json_dict_data.get("fail_list", [])) == 1)

    def test_delete_users_without_permission(self):
        student = self.login_first_with_student()
        username, password = str(uuid.uuid4())[:20], str(uuid.uuid4())[:20]
        admin = create_administrator(username, password, confirmed=True)
        username, password = str(uuid.uuid4())[:20], str(uuid.uuid4())[:20]
        teacher = create_teacher(username, password)
        rv = self.client.delete(url_for('account.delete_users'),
                                data=json.dumps([admin.id]),
                                content_type='application/json')
        self.assertTrue(getattr(rv, "status_code") == 403)

        rv = self.client.delete(url_for('account.delete_users'),
                                data=json.dumps(
                                    [teacher.id]),
                                content_type='application/json')
        self.assertTrue(getattr(rv, "status_code") == 403)

        rv = self.client.delete(url_for('account.delete_users'),
                                data=json.dumps(
                                    [student.id]),
                                content_type='application/json')
        self.assertTrue(getattr(rv, "status_code") == 403)




    ########################################
    # testcase for view "update_user_status"
    ######################################## 
    def test_update_user_status_with_nonexist_user(self):
        admin = self.login_first_with_admin()

        rv = self.client.put(url_for('account.update_user_status', id=admin.id+1), data=json.dumps(False), content_type = 'application/json')

        self.assertTrue(getattr(rv, "status_code") == 200)

        json_dict = json.loads(rv.data)

        self.assertTrue(json_dict.get("status", "") == "fail")
        self.assertTrue(json_dict.get("data", "") == "user not exist or super user")

    def test_update_user_status_with_exist_nonsuper_user(self):
        admin = self.login_first_with_admin()

        rv = self.client.put(url_for('account.update_user_status', id=admin.id), data=json.dumps(False), content_type = 'application/json')

        self.assertTrue(getattr(rv, "status_code") == 200)

        json_dict = json.loads(rv.data)

        self.assertTrue(json_dict.get("status", "") == "success")
        json_data = json_dict.get("data", {})
        self.assertEqual(json_data.get("id"), admin.id)
        self.assertTrue(not admin.is_active)

    def test_update_user_status_with_exist_super_user(self):
        # super user is whose username is admin
        admin = self.login_first_with_admin("admin")

        rv = self.client.put(url_for('account.update_user_status', id=admin.id), data=json.dumps(False), content_type = 'application/json')

        self.assertTrue(getattr(rv, "status_code") == 200)

        json_dict = json.loads(rv.data)

        self.assertTrue(json_dict.get("status", "") == "fail")
        self.assertTrue(json_dict.get("data", "") == "user not exist or super user")

    def test_update_user_status_without_permisssion(self):
        student = self.login_first_with_student()
        username, password = str(uuid.uuid4())[:20], str(uuid.uuid4())[:20]
        admin = create_administrator(username, password, confirmed=True)
        username, password = str(uuid.uuid4())[:20], str(uuid.uuid4())[:20]
        teacher = create_teacher(username, password)

        rv = self.client.put(url_for('account.update_user_status', id=admin.id),
                             data=json.dumps(False),
                             content_type='application/json')
        self.assertTrue(getattr(rv, "status_code") == 403)

        rv = self.client.put(url_for('account.update_user_status', id=teacher.id),
                             data=json.dumps(False),
                             content_type='application/json')
        self.assertTrue(getattr(rv, "status_code") == 403)

        rv = self.client.put(url_for('account.update_user_status', id=student.id),
                             data=json.dumps(False),
                             content_type='application/json')
        self.assertTrue(getattr(rv, "status_code") == 403)


    #################################
    # testcase for view "update_user"
    #################################
    def test_update_user_with_invalid_form(self):
        self.login_first_with_admin()

        rv = self.client.put(url_for('account.update_user', id="123"), data=dict())

        self.assertTrue(getattr(rv, "status_code") == 200)

        json_dict = json.loads(rv.data)
        self.assertTrue(json_dict.get("status", "") == "fail")

    def test_update_user_with_valid_form_and_nonexist_user(self):
        self.login_first_with_admin()

        rv = self.client.put(url_for('account.update_user', id="123"), data=dict(username="test", fullname="test", 
                                                                            email="test@vinzor.com"))
        self.assertTrue(getattr(rv, "status_code") == 200)

        json_dict = json.loads(rv.data)
        self.assertTrue(json_dict.get("status", "") == "fail")
        self.assertTrue(json_dict.get("data", "") == "user not exist")

    def test_update_user_with_valid_form_and_exist_user(self):
        admin = self.login_first_with_admin()

        rv = self.client.put(url_for('account.update_user', id="123"), data=dict(username=admin.username, fullname="test", 
                                                                            email="test@vinzor.com"))

        self.assertTrue(getattr(rv, "status_code") == 200)

        json_dict = json.loads(rv.data)
        self.assertTrue(json_dict.get("status", "") == "success")

        self.assertTrue(admin.fullname == "test")
        self.assertTrue(admin.email == "test@vinzor.com")

    def test_update_user_without_permission(self):
        student = self.login_first_with_student()
        username, password = str(uuid.uuid4())[:20], str(uuid.uuid4())[:20]
        admin = create_administrator(username, password, confirmed=True)
        username, password = str(uuid.uuid4())[:20], str(uuid.uuid4())[:20]
        teacher = create_teacher(username, password)

        rv = self.client.put(url_for('account.update_user', id="123"),
                             data=dict(username=admin.username, fullname="test",
                                       email="test@vinzor.com"))
        self.assertTrue(getattr(rv, "status_code") == 403)

        rv = self.client.put(url_for('account.update_user', id="124"),
                             data=dict(username=teacher.username, fullname="test",
                                       email="test1@vinzor.com"))
        self.assertTrue(getattr(rv, "status_code") == 403)

        rv = self.client.put(url_for('account.update_user', id="125"),
                             data=dict(username=admin.username, fullname="test",
                                       email="test2@vinzor.com"))
        self.assertTrue(getattr(rv, "status_code") == 403)


    #################################
    # testcase for view "export_user"
    #################################
    def test_export_user_with_teacher_role(self):
        self.login_first_with_admin()

        rv = self.client.get(url_for('account.export_user', role_name="Teacher"))

        self.assertTrue(getattr(rv, "status_code") == 200)

        self.assertEqual(rv.content_type, "application/vnd.ms-excel")

        # FIXME: this place can read the rv.data to judge the first line

    def test_export_user_with_nonteacher_role(self):
        self.login_first_with_admin()

        rv = self.client.get(url_for('account.export_user', role_name="Student"))

        self.assertTrue(getattr(rv, "status_code") == 200)

        self.assertEqual(rv.content_type, "application/vnd.ms-excel")

        # FIXME: this place can read the rv.data to judge the first line

    def test_export_user_without_permission(self):
        self.login_first_with_student()

        rv = self.client.get(
            url_for('account.export_user', role_name="Teacher"))
        self.assertTrue(getattr(rv, "status_code") == 403)

        rv = self.client.get(
            url_for('account.export_user', role_name="Student"))
        self.assertTrue(getattr(rv, "status_code") == 403)

    def test_export_user_with_nonteacher_and_nonstudent_role(self):
        self.login_first_with_admin()

        rv = self.client.get(
            url_for('account.export_user', role_name="Administrator"))
        self.assertTrue(getattr(rv, "status_code") == 403)


    #################################
    # testcase for view "upload_user"
    #################################
    def test_upload_user_with_none_file(self):
        self.login_first_with_admin()
        '''
        rv = self.client.post(url_for('account.upload_user'), buffered=True, content_type='multipart/form-data', data=dict(file=(io.BytesIO(b'1111'), "1.txt"), role="11"))
        print(rv.data, rv)
        self.assertTrue(getattr(rv, "status_code") == 200)

        json_dict = json.loads(rv.data)
        self.assertTrue(json_dict.get("status", "") == "fail")

        json_dict_data = json_dict.get("data", {})
        self.assertTrue(json_dict_data.get("error_msg", "") == "not post")
        '''


    ###################################
    # testcase for view "get_user_info"
    ###################################
    def test_get_user_info_with_exist_user(self):
        admin = self.login_first_with_admin()

        rv = self.client.post(url_for('account.get_user_info'), data=dict(userid=admin.username))

        self.assertTrue(getattr(rv, "status_code") == 200)

        json_dict = json.loads(rv.data)
        self.assertTrue(json_dict.get("userid", "") == admin.username)
        self.assertTrue(json_dict.get("fullname", "") == admin.fullname)

    def test_get_user_info_with_nonexist_user(self):
        self.login_first_with_admin()

        rv = self.client.post(url_for('account.get_user_info'), data=dict(userid="test"))

        self.assertTrue(getattr(rv, "status_code") == 200)

        json_dict = json.loads(rv.data)
        self.assertTrue(json_dict.get("status", "") == "fail")

    ####################################
    # testcase for view "modify_password"
    ####################################

if __name__ == "__main__":
    import unittest
    unittest.main()
