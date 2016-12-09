# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# comment
#
# 2016/4/22 qinjinghui : Init
__author__ = 'qinjinghui'

from base import FlaskTest
from utils import create_administrator, login_system, create_teacher, \
    create_student
from app.models import User, Desktop, Parameter, DesktopType, \
    DesktopTask
from flask import url_for, json
import time
from app import db
import datetime
import os
from phoenix.cloud import compute as OpenstackComputeService
from phoenix.cloud import image as OpenstackImageService

web_dir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
resource_dir = os.path.join(web_dir, 'resources')


class DesktopTest(FlaskTest):
    def setUp(self):
        super(DesktopTest, self).setUp()
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.client = self.app.test_client()

        # create a administrator to access the web system
        self.username = "admin"
        self.password = "admin123"
        create_administrator(self.username, self.password)

        self.t_username = "teacher"
        self.t_password = "admin123"
        create_teacher(self.t_username, self.t_password)

        self.s_username = "student"
        self.s_password = "admin123"
        create_student(self.s_username, self.s_password)

        # self.admin = User.query.filter_by(username=self.username).first()

    def test_course_desktop(self):
        # 暂时未有创建课程桌面的功能
        login_system(self.client, self.username, self.password)
        response = self.client.get(url_for('desktop.course_desktop'))
        result = response.data.decode('utf-8')
        # print(result)
        assert response.status_code == 200

        # 学生
        s_username = "student"
        s_password = "admin123"
        login_system(self.client, s_username, s_password)
        response = self.client.get(url_for('desktop.course_desktop'))
        assert response.status_code == 200

        # 教师
        t_username = "teacher"
        t_password = "admin123"
        login_system(self.client, t_username, t_password)
        response = self.client.get(url_for('desktop.course_desktop'))
        assert response.status_code == 200

    def test_static_desktop(self):
        # not get user permission
        login_system(self.client, self.username, self.password)
        user = User.query.filter_by(username=self.username).first()

        # create static desktop
        instance_name = "test_static_desktop"
        instance_image_id = "2d9e2df3-a6ce-4c40-9aa4-fdc709beca19"
        instance_flavor_id = "1"
        vm = OpenstackComputeService.create_server(name=instance_name,
                                                   image=instance_image_id,
                                                   flavor=instance_flavor_id)
        self.detect_create_vm_state(instance_name)
        desktop = Desktop()
        desktop.vm_ref = vm.id
        desktop.name = instance_name
        desktop.vm_state = "ACTIVE"
        desktop.desktop_type = DesktopType.STATIC
        desktop.owner_id = user.id
        desktop.end_datetime = datetime.datetime(3016, 1, 1, 0, 0, 0, 1)
        db.session.add(desktop)
        db.session.commit()

        response = self.client.get(url_for('desktop.static_desktop'))
        # print(response.data)

        assert instance_name in response.data.decode('utf-8')
        OpenstackComputeService.delete_server(vm.id)
        db.session.delete(desktop)
        db.session.commit()
        assert response.status_code == 200

    def test_free_desktop(self):
        ParamGroup.insert_default_groups()
        Parameter.insert_default_params()
        login_system(self.client, self.username, self.password)
        response = self.client.get(url_for('desktop.free_desktop'))
        assert response.status_code == 200

    def test_desktop_console(self):
        # get
        login_system(self.client, self.username, self.password)
        response = self.client.get(url_for('desktop.desktop_console'))
        result = response.data.decode("utf-8")
        assert "None" in result
        assert response.status_code == 200

        user = User.query.filter_by(username=self.username).first()
        # create static desktop
        instance_name = "test_console_desktop"
        instance_image_id = "2d9e2df3-a6ce-4c40-9aa4-fdc709beca19"
        instance_flavor_id = "1"
        vm = OpenstackComputeService.create_server(name=instance_name,
                                                   image=instance_image_id,
                                                   flavor=instance_flavor_id)
        self.detect_create_vm_state(instance_name)
        desktop = Desktop()
        desktop.vm_ref = vm.id
        desktop.name = instance_name
        desktop.vm_state = "ACTIVE"
        desktop.owner_id = user.id
        db.session.add(desktop)
        db.session.commit()

        # post
        # desktops = Desktop.query.filter_by(vm_state="ACTIVE").all()
        vmid = desktop.vm_ref
        response = self.client.post(url_for('desktop.desktop_console'),
                                    data=dict(id=vmid))
        result = response.data.decode("utf-8")

        assert desktop.name in result
        assert response.status_code == 200

        desktop.owner_id = None
        db.session.add(desktop)
        db.session.commit()
        response = self.client.post(url_for('desktop.desktop_console'),
                                    data=dict(id=vmid))
        result = response.data.decode("utf-8")
        assert "无人占用" in result

        # clear the test_console_desktop
        OpenstackComputeService.delete_server(vm.id)
        db.session.delete(desktop)
        db.session.commit()

    def test_add_time_by_vm(self):
        login_system(self.client, self.username, self.password)

        # create desktop
        instance_name = "test_add_time_desktop"
        instance_image_id = "2d9e2df3-a6ce-4c40-9aa4-fdc709beca19"
        instance_flavor_id = "1"
        vm = OpenstackComputeService.create_server(name=instance_name,
                                                   image=instance_image_id,
                                                   flavor=instance_flavor_id)
        self.detect_create_vm_state(instance_name)
        desktop = Desktop()
        desktop.vm_ref = vm.id
        desktop.name = instance_name
        desktop.vm_state = "ACTIVE"
        desktop.end_datetime = datetime.datetime(3016, 1, 1, 0, 0, 0, 1)
        db.session.add(desktop)
        try:
            db.session.commit()
        except Exception as ex:
            print('fail to add time by time!')
            db.session.rollback()

        hide_vmid = desktop.vm_ref
        add_time = "5"
        response = self.client.post(url_for('desktop.add_time_by_vm'),
                                    data=dict(hide_vmid=hide_vmid,
                                              add_time=add_time))
        result = json.loads(response.data)
        assert result['status'] == "success"

        # is not digit
        add_time = '五分钟'
        response = self.client.post(url_for('desktop.add_time_by_vm'),
                                    data=dict(hide_vmid=hide_vmid,
                                              add_time=add_time))

        result = json.loads(response.data)
        assert result['status'] == "fail"

        add_time = "1440"
        response = self.client.post(url_for('desktop.add_time_by_vm'),
                                    data=dict(hide_vmid=hide_vmid,
                                              add_time=add_time))

        result = json.loads(response.data)
        assert result['status'] == "more_than_one_day"

        # clear the test_console_desktop
        OpenstackComputeService.delete_server(vm.id)
        db.session.delete(desktop)
        db.session.commit()

    def test_refresh_state(self):
        pass


    def test_create_static_desktop(self):
        login_system(self.client, self.username, self.password)
        owner = "admin"
        # cirros-0.3.2
        template = "2d9e2df3-a6ce-4c40-9aa4-fdc709beca19"
        # 1VCPU|512MB|1GB
        flavor = "1"
        response = self.client.post(url_for('desktop.create_static_desktop'),
                                    data=dict(owner=owner, template=template,
                                              flavor=flavor))
        result = json.loads(response.data)
        assert result['status'] == "success"

        self.detect_create_static_desktop()
        desktop = Desktop.query.first()
        OpenstackComputeService.delete_server(desktop.vm_ref)
        db.session.delete(desktop)
        db.session.commit()

        # 错误用户
        owner = "adminhaha"
        # cirros-0.3.2
        template = "2d9e2df3-a6ce-4c40-9aa4-fdc709beca19"
        # 1VCPU|512MB|1GB
        flavor = "1"
        response = self.client.post(url_for('desktop.create_static_desktop'),
                                    data=dict(owner=owner, template=template,
                                              flavor=flavor))
        result = json.loads(response.data)
        assert result['status'] == "noneuser"

    # def test_batch_add_static_desktops(self):
    #     login_system(self.client, self.username, self.password)
    #     student = User.query.filter_by(username=self.s_username).first()
    #
    #     # create static desktop
    #     instance_name = "test_batch_add_static_desktop"
    #     instance_image_id = "2d9e2df3-a6ce-4c40-9aa4-fdc709beca19"
    #     instance_flavor_id = "1"
    #     vm = OpenstackComputeService.create_server(name=instance_name,
    #                                                image=instance_image_id,
    #                                                flavor=instance_flavor_id)
    #     self.detect_create_vm_state(instance_name)
    #     desktop = Desktop()
    #     desktop.vm_ref = vm.id
    #     desktop.name = instance_name
    #     desktop.vm_state = "ACTIVE"
    #     desktop.owner_id = student.id
    #     desktop.end_datetime = datetime.datetime(3016, 1, 1, 0, 0, 0, 1)
    #     db.session.add(desktop)
    #     db.session.commit()
    #
    #     # read file
    #     f = open(os.path.join(resource_dir, '固定桌面导入模板.xls'), 'rb')
    #     response = self.client.post(url_for(
    #         'desktop.batch_add_static_desktops'),
    #         data={"file": f})
    #     result = json.loads(response.data)
    #     f.close()
    #
    #     #clear the test_console_desktop
    #     OpenstackComputeService.delete_server(vm.id)
    #     db.session.delete(desktop)
    #     db.session.commit()
    #
    #     assert result['fail_list'][0]['info'] == "桌面已存在"
    #     assert result['fail_list'][1]['info'] == "用户不存在"
    #     assert result['fail_list'][2]['info'] == "模板或配置不存在"
    #     assert result['fail_list'][3]['info'] == "模板或配置不存在"
    #     assert result['fail_list'][4]['info'] == "配置不存在"
    #     assert result['fail_list'][5]['info'] == "模板不存在"
    #     assert result['fail_list'][6]['info'] == "用户不存在"
    #     # 全部失败，状态仍未success
    #     assert result['status'] == "part fail"
    #     assert response.status_code == 200
    #
    #     f = open(os.path.join(resource_dir, 'for_test.py'), 'rb')
    #     response = self.client.post(url_for(
    #         'desktop.batch_add_static_desktops'),
    #         data={"file": f})
    #     result = json.loads(response.data)
    #     f.close()
    #     assert result['error_msg'] == 'type error'
    #     assert result['status'] == 'fail'
    #
    #     self.detect_create_static_desktop()
    #     desktop = Desktop.query.first()
    #     OpenstackComputeService.delete_server(desktop.vm_ref)
    #     db.session.delete(desktop)
    #     db.session.commit()

    def test_delete_static_desktop(self):
        login_system(self.client, self.username, self.password)

        # create desktop
        instance_name = "test_delete_static_desktop"
        instance_image_id = "2d9e2df3-a6ce-4c40-9aa4-fdc709beca19"
        instance_flavor_id = "1"
        vm = OpenstackComputeService.create_server(name=instance_name,
                                                   image=instance_image_id,
                                                   flavor=instance_flavor_id)
        self.detect_create_vm_state(instance_name)
        desktop = Desktop()
        desktop.vm_ref = vm.id
        desktop.name = instance_name
        desktop.vm_state = "ACTIVE"
        desktop.end_datetime = datetime.datetime(3016, 1, 1, 0, 0, 0, 1)
        db.session.add(desktop)
        db.session.commit()

        static_desktops = []
        static_desktops.append(desktop.vm_ref)
        response = self.client.post(url_for('desktop.delete_static_desktop'),
                                    data={
                                        "static_desktopids[]": static_desktops})
        result = json.loads(response.data)

        # clear the test_console_desktop
        OpenstackComputeService.delete_server(vm.id)
        db.session.delete(desktop)
        db.session.commit()

        assert result['status'] == "success"


    def test_delete_free_desktops(self):
        pass

    def test_reboot_vm(self):
        login_system(self.client, self.username, self.password)

        # create desktop
        instance_name = "test_reboot_desktop"
        instance_image_id = "2d9e2df3-a6ce-4c40-9aa4-fdc709beca19"
        instance_flavor_id = "1"
        vm = OpenstackComputeService.create_server(name=instance_name,
                                                   image=instance_image_id,
                                                   flavor=instance_flavor_id)
        self.detect_create_vm_state(instance_name)
        desktop = Desktop()
        desktop.vm_ref = vm.id
        desktop.name = instance_name
        desktop.vm_state = "ACTIVE"
        desktop.end_datetime = datetime.datetime(3016, 1, 1, 0, 0, 0, 1)
        db.session.add(desktop)
        db.session.commit()

        vmid = desktop.vm_ref
        response = self.client.post(url_for('desktop.reboot_vm'), data=dict(
            vmid=vmid))
        result = json.loads(response.data)

        # clear the test_console_desktop
        self.detect_reboot_vm_state(instance_name)
        OpenstackComputeService.delete_server(vm.id)
        db.session.delete(desktop)
        db.session.commit()
        assert result['status'] == "success"

        vmid = "ttt"
        response = self.client.post(url_for('desktop.reboot_vm'), data=dict(
            vmid=vmid))
        result = json.loads(response.data)
        assert result['status'] == "Notexist"

        # reboot缺少返回值
        vmid = ""
        response = self.client.post(url_for('desktop.reboot_vm'), data=dict(
            vmid=vmid))
        result = json.loads(response.data)
        assert result['status'] == "fail"

    def test_suspend_vm(self):
        """
        关闭/挂起桌面
        :return:
        """
        login_system(self.client, self.username, self.password)

        # create desktop
        instance_name = "test_suspend_desktop"
        instance_image_id = "2d9e2df3-a6ce-4c40-9aa4-fdc709beca19"
        instance_flavor_id = "1"
        vm = OpenstackComputeService.create_server(name=instance_name,
                                                   image=instance_image_id,
                                                   flavor=instance_flavor_id)
        self.detect_create_vm_state(instance_name)
        desktop = Desktop()
        desktop.vm_ref = vm.id
        desktop.name = instance_name
        desktop.vm_state = "ACTIVE"
        desktop.end_datetime = datetime.datetime(3016, 1, 1, 0, 0, 0, 1)
        db.session.add(desktop)
        db.session.commit()

        vmid = desktop.vm_ref
        response = self.client.post(url_for('desktop.suspend_vm'),
                                    data=dict(
                                        vmid=vmid))
        result = json.loads(response.data)

        self.detect_suspend_vm_state(instance_name)
        OpenstackComputeService.delete_server(vm.id)
        db.session.delete(desktop)
        db.session.commit()

        assert result['status'] == "success"

        vmid = "ttt"
        response = self.client.post(url_for('desktop.suspend_vm'),
                                    data=dict(
                                        vmid=vmid))
        result = json.loads(response.data)
        assert result['status'] == "Notexist"

        vmid = ""
        response = self.client.post(url_for('desktop.suspend_vm'), data=dict(
            vmid=vmid))
        result = json.loads(response.data)
        assert result['status'] == "fail"

    def test_resume_vm(self):
        """
        开启桌面
        :return:
        """
        login_system(self.client, self.username, self.password)
        # create desktop
        instance_name = "test_resume_desktop"
        instance_image_id = "2d9e2df3-a6ce-4c40-9aa4-fdc709beca19"
        instance_flavor_id = "1"
        vm = OpenstackComputeService.create_server(name=instance_name,
                                                   image=instance_image_id,
                                                   flavor=instance_flavor_id)
        self.detect_create_vm_state(instance_name)
        OpenstackComputeService.suspend_server(vm.id)
        self.detect_suspend_vm_state(instance_name)
        desktop = Desktop()
        desktop.vm_ref = vm.id
        desktop.name = instance_name
        desktop.vm_state = "SUSPENDED"
        desktop.end_datetime = datetime.datetime(3016, 1, 1, 0, 0, 0, 1)
        db.session.add(desktop)
        db.session.commit()

        vmid = desktop.vm_ref
        response = self.client.post(url_for('desktop.resume_vm'), data=dict(
            vmid=vmid))
        result = json.loads(response.data)

        # clear the test_console_desktop
        self.detect_resume_vm_state(instance_name)
        OpenstackComputeService.delete_server(vm.id)
        db.session.delete(desktop)
        db.session.commit()

        assert result['status'] == "success"

        vmid = "ttt"
        response = self.client.post(url_for('desktop.resume_vm'), data=dict(
            vmid=vmid))
        result = json.loads(response.data)
        assert result['status'] == "Notexist"

        vmid = ""
        response = self.client.post(url_for('desktop.resume_vm'), data=dict(
            vmid=vmid))
        result = json.loads(response.data)
        assert result['status'] == "fail"

    def test_rebuild_desktop(self):
        login_system(self.client, self.username, self.password)

        # create desktop
        instance_name = "test_rebuild_desktop"
        instance_image_id = "2d9e2df3-a6ce-4c40-9aa4-fdc709beca19"
        instance_flavor_id = "1"
        vm = OpenstackComputeService.create_server(name=instance_name,
                                                   image=instance_image_id,
                                                   flavor=instance_flavor_id)
        self.detect_create_vm_state(instance_name)
        desktop = Desktop()
        desktop.vm_ref = vm.id
        desktop.name = instance_name
        desktop.vm_state = "ACTIVE"
        desktop.end_datetime = datetime.datetime(3016, 1, 1, 0, 0, 0, 1)
        db.session.add(desktop)
        db.session.commit()

        vmid = desktop.vm_ref
        response = self.client.post(url_for('desktop.rebuild_desktop'),
                                    data=dict(
                                        vmid=vmid))
        result = json.loads(response.data)

        # clear the test_console_desktop
        self.detect_rebuild_vm_state(instance_name)
        OpenstackComputeService.delete_server(vm.id)
        db.session.delete(desktop)
        db.session.commit()

        assert result['status'] == "success"

        vmid = "ttt"
        response = self.client.post(url_for('desktop.rebuild_desktop'),
                                    data=dict(
                                        vmid=vmid))
        result = json.loads(response.data)
        assert result['status'] == "Notexist"

        vmid = ""
        response = self.client.post(url_for('desktop.rebuild_desktop'),
                                    data=dict(
                                        vmid=vmid))
        result = json.loads(response.data)
        # print(result)
        assert result['status'] == "fail"


    # @staticmethod
    # def detect_desktop_tasks():
    #     desktop_tasks = DesktopTask.query.filter(DesktopTask.state !=
    #                                              'FINISHED').first()
    #     while True:
    #         if desktop_tasks.state == 'FINISHED':
    #             break
    #         else:
    #             time.sleep(3)


    @staticmethod
    def detect_create_static_desktop():
        while True:
            desktop = Desktop.query.first()
            if desktop:
                vm_name = desktop.name
                status = OpenstackComputeService.get_server_by_name(
                    vm_name).status
                if status == 'BUILD':
                    time.sleep(3)
                elif status == 'ACTIVE':
                    break
                else:
                    raise ValueError

    @staticmethod
    def detect_create_vm_state(vm_name):
        while True:
            status = OpenstackComputeService.get_server_by_name(vm_name).status
            if status == 'BUILD':
                time.sleep(3)
            elif status == 'ACTIVE':
                break
            else:
                raise ValueError

    @staticmethod
    def detect_suspend_vm_state(vm_name):
        while True:
            status = OpenstackComputeService.get_server_by_name(vm_name).status
            if status != 'SUSPENDED':
                time.sleep(3)
            elif status == 'SUSPENDED':
                break
            else:
                raise ValueError

    @staticmethod
    def detect_rebuild_vm_state(vm_name):
        while True:
            status = OpenstackComputeService.get_server_by_name(vm_name).status
            if status != 'ACTIVE':
                time.sleep(3)
            elif status == 'ACTIVE':
                break
            else:
                raise ValueError

    @staticmethod
    def detect_resume_vm_state(vm_name):
        while True:
            status = OpenstackComputeService.get_server_by_name(vm_name).status
            if status == 'SUSPENDED':
                time.sleep(3)
            elif status == 'ACTIVE':
                break
            else:
                raise ValueError

    @staticmethod
    def detect_reboot_vm_state(vm_name):
        while True:
            status = OpenstackComputeService.get_server_by_name(vm_name).status
            if status != 'ACTIVE':
                time.sleep(3)
            elif status == 'ACTIVE':
                break
            else:
                raise ValueError

    def tearDown(self):
        User.query.delete()
        Desktop.query.delete()
        Parameter.query.delete()
        ParamGroup.query.delete()
        # DesktopTask.query.delete()
        # DesktopTaskExtra.query.delete()
        super(DesktopTest, self).tearDown()
