# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# comment
#
# 2016/5/7 zhuwenbiao : Init
__author__ = 'zwb'

import uuid
import os
import sys
import random
import time
from base import FlaskTest
from flask import json, jsonify
from app import app, db
from flask import url_for
from utils import create_administrator, login_system, create_course, \
    create_student, create_teacher, create_personal_storage
from app.common import password_utils
from app.storage import utils
from app.models import FtpServer, Course, FtpAccount, SambaServer, \
    SambaAccount, User

web_dir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
resource_dir = os.path.join(web_dir, 'resources')


class StorageTest(FlaskTest):
    def setUp(self):
        super(StorageTest, self).setUp()
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.username = "admin"
        self.password = "admin123"
        self.client = self.app.test_client()
        create_administrator(self.username, self.password)
        create_teacher("teacher", "admin123")
        create_student("student", "admin123")
        create_course("test_course", "teacher")

    def test_share(self):
        login_system(self.client, self.username, self.password)
        response = self.client.get(url_for('storage.share'))
        assert response.status_code == 200

    def test_add_share(self):
        login_system(self.client, self.username, self.password)
        name = "openstack"
        ip = "222.200.185.38"
        port = random.randint(1, 65535)
        response = self.client.post(url_for('storage.add_share'), data=dict(
            name=name, ip=ip, port=port))
        result = json.loads(response.data)
        assert result['status'] == "success"

        name = uuid.uuid4()
        response = self.client.post(url_for('storage.add_share'), data=dict(
            name=name, ip=ip, port=port))
        result = json.loads(response.data)
        assert result['status'] == "existed"

        name = ""
        ip = ""
        port = ""
        response = self.client.post(url_for('storage.add_share'), data=dict(
            name=name, ip=ip, port=port))
        result = json.loads(response.data)
        assert result['status'] == "fail"

    def test_delete_share(self):
        login_system(self.client, self.username, self.password)
        name = "openstack"
        ip = "222.200.185.38"
        port = random.randint(1, 65535)
        self.client.post(url_for('storage.add_share'), data=dict(
            name=name, ip=ip, port=port))

        name = uuid.uuid4()
        ip = "222.200.10.10"
        port = random.randint(1, 65535)
        self.client.post(url_for('storage.add_share'), data=dict(
            name=name, ip=ip, port=port))

        id = [1000]
        response = self.client.post(url_for('storage.delete_share'),
                                    data={"ids[]": id})
        result = json.loads(response.data)
        assert result['status'] == "fail"

        ftp_list = FtpServer.query.all()
        ids = []
        for it in ftp_list:
            ids.append(it.id)
        response = self.client.post(url_for('storage.delete_share'),
                                    data={"ids[]": ids})
        result = json.loads(response.data)
        assert result['status'] == "success"

    def test_update_share(self):
        login_system(self.client, self.username, self.password)

        name = "openstack"
        ip = "222.200.185.38"
        port = random.randint(1, 65535)
        self.client.post(url_for('storage.add_share'), data=dict(
            name=name, ip=ip, port=port))

        ftp_server = FtpServer.query.first()
        ftp_id = ftp_server.id
        name = ftp_server.name
        ip = ftp_server.ip
        port = ftp_server.port
        response = self.client.post(url_for('storage.update_share'),
                                    data=dict(ftp_id=ftp_id, name=name,
                                              ip=ip, port=port))
        result = json.loads(response.data)
        assert result['status'] == "existed"

        port = random.randint(1, 65535)
        response = self.client.post(url_for('storage.update_share'),
                                    data=dict(ftp_id=ftp_id, name=name,
                                              ip=ip, port=port))
        result = json.loads(response.data)
        assert result['status'] == "success"

        ftp_id = 1000
        port = random.randint(1, 65535)
        response = self.client.post(url_for('storage.update_share'),
                                    data=dict(ftp_id=ftp_id, name=name,
                                              ip=ip, port=port))
        result = json.loads(response.data)
        assert result['status'] == "fail"

    def test_share_account(self):
        login_system(self.client, self.username, self.password)
        response = self.client.get(url_for('storage.share_account'))
        assert response.status_code == 200

    def test_add_share_account(self):
        login_system(self.client, self.username, self.password)

        name = "openstack"
        ip = "222.200.185.38"
        port = random.randint(1, 65535)
        self.client.post(url_for('storage.add_share'), data=dict(
            name=name, ip=ip, port=port))
        ftp_server = FtpServer.query.first()
        # 暂时用默认的test课程
        share_course = Course.query.first()

        ftp = ftp_server.id
        course = share_course.id
        username = "openstack"
        password = "te$t123"
        response = self.client.post(url_for('storage.add_share_account'),
                                    data=dict(course=course, ftp=ftp,
                                              username=username,
                                              password=password))
        result = json.loads(response.data)
        assert result['status'] == "success"

        response = self.client.post(url_for('storage.add_share_account'),
                                    data=dict(course=course, ftp=ftp,
                                              username=username,
                                              password=password))
        result = json.loads(response.data)
        assert result['status'] == "existed"

        password = uuid.uuid4()
        response = self.client.post(url_for('storage.add_share_account'),
                                    data=dict(course=course, ftp=ftp,
                                              username=username,
                                              password=password))
        result = json.loads(response.data)
        assert result['status'] == "ftp_fail"

    def test_update_share_account(self):
        """
        :param: account_id, course_id, ftp_id, username, password
        """
        login_system(self.client, self.username, self.password)

        name = "openstack"
        ip = "222.200.185.38"
        port = random.randint(1, 65535)
        self.client.post(url_for('storage.add_share'), data=dict(
            name=name, ip=ip, port=port))
        ftp_server = FtpServer.query.first()
        # 暂时用默认的test课程
        share_course = Course.query.first()

        ftp = ftp_server.id
        course = share_course.id
        username = "openstack"
        password = "te$t123"
        self.client.post(url_for('storage.add_share_account'),
                         data=dict(course=course, ftp=ftp,
                                   username=username,
                                   password=password))

        share_account = FtpAccount.query.first()
        account_id = share_account.id
        response = self.client.post(url_for('storage.update_share_account'),
                                    data=dict(account_id=account_id,
                                              course=course,
                                              ftp=ftp,
                                              username=username,
                                              password=password))
        result = json.loads(response.data)
        assert result['status'] == "existed"

        # 创建新的课程
        share_course = create_course("haha", "teacher")
        course = share_course.id
        response = self.client.post(url_for('storage.update_share_account'),
                                    data=dict(account_id=account_id,
                                              course=course,
                                              ftp=ftp,
                                              username=username,
                                              password=password))
        result = json.loads(response.data)
        assert result['status'] == 'success'

        password = uuid.uuid4()
        response = self.client.post(url_for('storage.update_share_account'),
                                    data=dict(account_id=account_id,
                                              course=course,
                                              ftp=ftp,
                                              username=username,
                                              password=password))
        result = json.loads(response.data)
        assert result['status'] == "ftp_fail"

    def test_delete_share_account(self):
        login_system(self.client, self.username, self.password)

        name = "openstack"
        ip = "222.200.185.38"
        port = random.randint(1, 65535)
        self.client.post(url_for('storage.add_share'), data=dict(
            name=name, ip=ip, port=port))
        ftp_server = FtpServer.query.first()
        # 暂时用默认的test课程
        share_course = Course.query.first()

        ftp = ftp_server.id
        course = share_course.id
        username = "openstack"
        password = "te$t123"
        self.client.post(url_for('storage.add_share_account'),
                         data=dict(course=course, ftp=ftp,
                                   username=username,
                                   password=password))

        share_accounts = FtpAccount.query.all()
        ids = []
        for it in share_accounts:
            ids.append(it.id)
        response = self.client.post(url_for('storage.delete_share_account'),
                                    data={"ids[]": ids})
        result = json.loads(response.data)
        assert result['status'] == "success"

        ids = []
        response = self.client.post(url_for('storage.delete_share_account'),
                                    data={"ids[]:": ids})
        result = json.loads(response.data)
        assert result['status'] == "fail"

    def test_personal(self):
        login_system(self.client, self.username, self.password)
        response = self.client.get(url_for('storage.personal'))
        assert response.status_code == 200

    def test_add_personal_storage(self):
        login_system(self.client, self.username, self.password)
        name = "samba"
        ip = "172.18.231.251"
        administrator = "admin"
        password = "admin12"

        response = self.client.post(url_for('storage.add_personal_storage'),
                                    data=dict(name=name, ip=ip,
                                              administrator=administrator,
                                              password=password))
        result = json.loads(response.data)
        # print(result)
        assert result['status'] == 'pswd_error'

        password = 'admin123'
        response = self.client.post(url_for('storage.add_personal_storage'),
                                    data=dict(name=name, ip=ip,
                                              administrator=administrator,
                                              password=password))
        result = json.loads(response.data)
        # print(result)
        assert result['status'] == 'success'

        response = self.client.post(url_for('storage.add_personal_storage'),
                                    data=dict(name=name, ip=ip,
                                              administrator=administrator,
                                              password=password))
        result = json.loads(response.data)
        assert result['status'] == 'existed'

        ip = "172.18.231.240"
        password = "admin123"
        response = self.client.post(url_for('storage.add_personal_storage'),
                                    data=dict(name=name, ip=ip,
                                              administrator=administrator,
                                              password=password))
        result = json.loads(response.data)
        # print(result)
        assert result['status'] == 'connect_fail'

    def test_update_personal_storage(self):
        login_system(self.client, self.username, self.password)
        name = "samba"
        ip = "172.18.231.251"
        administrator = "admin"
        password = "admin123"
        self.client.post(url_for('storage.add_personal_storage'),
                         data=dict(name=name, ip=ip,
                                   administrator=administrator,
                                   password=password))

        samba_server = SambaServer.query.filter_by(name='samba').first()
        samba_id = samba_server.id

        # only update name
        name = 'samba_change_name'
        password = ''
        response = self.client.post(url_for('storage.update_personal_storage'),
                                    data=dict(samba_id=samba_id, name=name,
                                              ip=ip,
                                              administrator=administrator,
                                              password=password))
        result = json.loads(response.data)
        assert result['status'] == 'success'

        # 更新个人服务器
        name = "samba-test"
        ip = "172.18.231.250"
        administrator = "admin"
        password = "admin12"
        response = self.client.post(url_for('storage.update_personal_storage'),
                                    data=dict(samba_id=samba_id, name=name,
                                              ip=ip,
                                              administrator=administrator,
                                              password=password))
        result = json.loads(response.data)
        assert result['status'] == 'pswd_error'

        ip = '172.18.231.100'
        response = self.client.post(url_for('storage.update_personal_storage'),
                                    data=dict(samba_id=samba_id, name=name,
                                              ip=ip,
                                              administrator=administrator,
                                              password=password))
        result = json.loads(response.data)
        assert result['status'] == 'connect_fail'

        ip = "172.18.231.250"
        password = 'admin123'
        response = self.client.post(url_for('storage.update_personal_storage'),
                                    data=dict(samba_id=samba_id, name=name,
                                              ip=ip,
                                              administrator=administrator,
                                              password=password))
        result = json.loads(response.data)
        assert result['status'] == 'success'

        # 添加个人服务器
        name = "samba"
        ip = "172.18.231.251"
        administrator = "admin"
        password = "admin123"
        self.client.post(url_for('storage.add_personal_storage'),
                         data=dict(name=name, ip=ip,
                                   administrator=administrator,
                                   password=password))

        samba_server = SambaServer.query.filter_by(name="samba").first()
        samba_id = samba_server.id
        ip = '172.18.231.250'
        response = self.client.post(url_for(
            'storage.update_personal_storage'), data=dict(samba_id=samba_id,
                                                          name=name,
                                                          ip=ip,
                                                          administrator=administrator,
                                                          password=password))
        result = json.loads(response.data)
        assert result['status'] == 'existed'

    def test_delete_personal_storage(self):
        login_system(self.client, self.username, self.password)
        name = "samba"
        ip = "172.18.231.251"
        administrator = "admin"
        password = "admin123"
        self.client.post(url_for('storage.add_personal_storage'),
                         data=dict(name=name, ip=ip,
                                   administrator=administrator,
                                   password=password))

        samba_server = SambaServer.query.all()
        ids = []
        for it in samba_server:
            ids.append(it.id)
        response = self.client.post(url_for(
            'storage.delete_personal_storage'), data={"ids[]": ids})
        result = json.loads(response.data)
        assert result['status'] == 'success'

        ids = [1000]
        response = self.client.post(url_for(
            'storage.delete_personal_storage'), data={"ids[]": ids})
        result = json.loads(response.data)
        # print(result)
        assert result['status'] == 'fail'

        ids = []
        response = self.client.post(url_for(
            'storage.delete_personal_storage'), data={"ids[]": ids})
        result = json.loads(response.data)
        # print(result)
        assert result['status'] == 'success'

    def test_personal_acconut(self):
        login_system(self.client, self.username, self.password)
        response = self.client.get(url_for('storage.personal_account'))
        assert response.status_code == 200

    def test_add_personal_account(self):
        """
        :param: samba, user, quota
        密码自动生成
        """
        login_system(self.client, self.username, self.password)

        samba = 100
        user = User.query.filter_by(username='student').first().id
        quota = random.randint(1, 30)
        response = self.client.post(url_for('storage.add_personal_account'),
                                    data=dict(samba=samba, user=user,
                                              quota=quota))
        result = json.loads(response.data)
        # print(result)
        assert result['status'] == 'fail'

        name = "samba"
        ip = "172.18.231.251"
        administrator = "admin"
        password = "admin123"
        self.client.post(url_for('storage.add_personal_storage'),
                         data=dict(name=name, ip=ip,
                                   administrator=administrator,
                                   password=password))

        # 向数据库中加入无效服务器模拟无效链接
        ip = '172.18.231.200'
        create_personal_storage("samba-test", ip, administrator, password)

        samba = SambaServer.query.filter_by(ip='172.18.231.200').first().id
        user = User.query.filter_by(username='student').first().id
        quota = 1
        response = self.client.post(url_for('storage.add_personal_account'),
                                    data=dict(samba=samba, user=user,
                                              quota=quota))
        result = json.loads(response.data)
        assert result['status'] == 'connect_fail'

        samba = SambaServer.query.first().id
        user = User.query.filter_by(username='student').first().id
        quota = 0
        response = self.client.post(url_for('storage.add_personal_account'),
                                    data=dict(samba=samba, user=user,
                                              quota=quota))
        result = json.loads(response.data)
        assert result['status'] == 'fail'

        quota = random.randint(1, 30)
        response = self.client.post(url_for('storage.add_personal_account'),
                                    data=dict(samba=samba, user=user,
                                              quota=quota))
        result = json.loads(response.data)
        assert result['status'] == 'success'

        response = self.client.post(url_for('storage.add_personal_account'),
                                    data=dict(samba=samba, user=user,
                                              quota=quota))
        result = json.loads(response.data)
        assert result['status'] == 'existed'

        ids = []
        samba_accounts = SambaAccount.query.all()
        for it in samba_accounts:
            ids.append(it.id)
        self.client.post(url_for(
            'storage.delete_personal_account'), data={'ids[]': ids})

    def test_update_personal_account(self):
        """
        :param: account, samba, user, quota
        """
        login_system(self.client, self.username, self.password)
        name = "samba"
        ip = "172.18.231.251"
        administrator = "admin"
        password = "admin123"
        self.client.post(url_for('storage.add_personal_storage'),
                         data=dict(name=name, ip=ip,
                                   administrator=administrator,
                                   password=password))
        samba = SambaServer.query.first().id
        user = User.query.filter_by(username='student').first().id
        quota = random.randint(1, 30)
        self.client.post(url_for('storage.add_personal_account'),
                         data=dict(samba=samba, user=user, quota=quota))

        account = SambaAccount.query.first().id

        quota = random.randint(1, 30)
        response = self.client.post(url_for(
            'storage.update_personal_account'), data=dict(account=account,
                                                          samba=samba,
                                                          user=user,
                                                          quota=quota))
        result = json.loads(response.data)
        assert result['status'] == 'success'

        # 创建无效账户
        ip = '172.18.231.200'
        create_personal_storage("samba-test", ip, administrator, password)

        samba = SambaServer.query.filter_by(ip=ip).first().id
        quota = random.randint(1, 30)
        new_account = SambaAccount()
        new_account.samba_server_id = samba
        new_account.user_id = user
        new_account.password = password_utils.encrypt(
            utils.generate_random_passwd())
        new_account.quota = str(quota) + 'GB'
        db.session.add(new_account)
        db.session.commit()
        account = SambaAccount.query.filter_by(samba_server_id=samba).first().id
        response = self.client.post(url_for(
            'storage.update_personal_account'), data=dict(account=account,
                                                          samba=samba,
                                                          user=user,
                                                          quota=quota))
        result = json.loads(response.data)
        assert result['status'] == 'connect_fail'

        samba = SambaServer.query.first().id
        account = 100
        quota = random.randint(1, 30)
        response = self.client.post(url_for(
            'storage.update_personal_account'), data=dict(account=account,
                                                          samba=samba,
                                                          user=user,
                                                          quota=quota))
        result = json.loads(response.data)
        assert result['status'] == 'fail'

        ids = []
        samba_accounts = SambaAccount.query.all()
        for it in samba_accounts:
            ids.append(it.id)
        self.client.post(url_for(
            'storage.delete_personal_account'), data={'ids[]': ids})

    def test_delete_personal_account(self):
        """
        :param: samba_account_ids
        """
        login_system(self.client, self.username, self.password)
        name = "samba"
        ip = "172.18.231.251"
        administrator = "admin"
        password = "admin123"
        self.client.post(url_for('storage.add_personal_storage'),
                         data=dict(name=name, ip=ip,
                                   administrator=administrator,
                                   password=password))
        samba = SambaServer.query.first().id
        user = User.query.filter_by(username='student').first().id
        quota = random.randint(1, 30)
        self.client.post(url_for('storage.add_personal_account'),
                         data=dict(samba=samba, user=user,
                                   quota=quota))
        user = User.query.filter_by(username='teacher').first().id
        quota = random.randint(1, 30)
        self.client.post(url_for('storage.add_personal_account'),
                         data=dict(samba=samba, user=user,
                                   quota=quota))

        name = "samba-test"
        ip = "172.18.231.250"
        administrator = "admin"
        password = "admin123"
        self.client.post(url_for('storage.add_personal_storage'),
                         data=dict(name=name, ip=ip,
                                   administrator=administrator,
                                   password=password))
        samba = SambaServer.query.filter_by(name='samba-test').first().id
        user = User.query.filter_by(username='teacher').first().id
        quota = random.randint(1, 30)
        self.client.post(url_for('storage.add_personal_account'),
                         data=dict(samba=samba, user=user,
                                   quota=quota))

        ids = []
        samba_accounts = SambaAccount.query.all()
        for it in samba_accounts:
            ids.append(it.id)
        response = self.client.post(url_for(
            'storage.delete_personal_account'), data={'ids[]': ids})
        result = json.loads(response.data)
        assert result['status'] == 'success'

        samba_accounts = SambaAccount.query.all()
        assert len(samba_accounts) == 0

    def test_upload_personal_account(self):
        login_system(self.client, self.username, self.password)
        name = "samba"
        ip = "172.18.231.251"
        administrator = "admin"
        password = "admin123"
        self.client.post(url_for('storage.add_personal_storage'),
                         data=dict(name=name, ip=ip,
                                   administrator=administrator,
                                   password=password))

        name = "samba-test"
        ip = "172.18.231.250"
        administrator = "admin"
        password = "admin123"
        self.client.post(url_for('storage.add_personal_storage'),
                         data=dict(name=name, ip=ip,
                                   administrator=administrator,
                                   password=password))

        # add personal account into database
        samba = SambaServer.query.first().id
        user = User.query.filter_by(username='teacher').first().id
        quota = 1
        self.client.post(url_for('storage.add_personal_account'),
                         data=dict(samba=samba, user=user,
                                   quota=quota))

        ip = '172.18.231.200'
        create_personal_storage("samba-2", ip, administrator, password)

        f = open(os.path.join(resource_dir, '个人文件夹账号导入模板.xls'), 'rb')
        response = self.client.post(url_for(
            'storage.upload_personal_account'),
            data={"file": f})
        result = json.loads(response.data)
        print(result)
        assert result['status'] == 'part fail'
        assert result['fail_list'][0]['info'] == '空间大小格式不正确（整数GB）'
        assert result['fail_list'][1]['info'] == '用户ID不存在'
        assert result['fail_list'][2]['info'] == '个人文件服务器不存在'
        assert result['fail_list'][3]['info'] == '用户已经存在'
        assert result['fail_list'][4]['info'] == '空间大小格式不正确（整数GB）'
        assert result['fail_list'][5]['info'] == '磁盘配额超过物理硬盘的总容量'
        assert result['fail_list'][6]['info'] == '磁盘配额超过物理硬盘的总容量'
        assert result['fail_list'][7]['info'] == '磁盘配额超过物理硬盘的总容量'
        assert result['fail_list'][8]['info'] == '个人文件服务器连接失败'

        ids = []
        samba_accounts = SambaAccount.query.all()
        for it in samba_accounts:
            ids.append(it.id)
        self.client.post(url_for(
            'storage.delete_personal_account'), data={'ids[]': ids})

    def tearDown(self):
        User.query.delete()
        FtpServer.query.delete()
        Course.query.delete()
        FtpAccount.query.delete()
        SambaServer.query.delete()
        SambaAccount.query.delete()
        db.session.commit()
        super(StorageTest, self).tearDown()
