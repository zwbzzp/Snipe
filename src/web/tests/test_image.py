# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# comment
#
# 2016/4/22 qinjinghui : Init
# 2016/5/5  wuhaibin: Modified
__author__ = 'qinjinghui'


import time
from base import FlaskTest
from flask import json, jsonify

from phoenix.cloud import compute as OpenstackComputeService
from phoenix.cloud import image as OpenstackImageService
from web.manage import beat
from app.models import   Desktop
from app import db
from utils import create_administrator, login_system


class ImageTest(FlaskTest):

    def setUp(self):
        super(ImageTest, self).setUp()
        self.app.config['WTF_CSRF_ENABLED'] = False

        # create a administrator to access the web system
        self.username = "admin"
        self.password = "admin123"
        create_administrator(self.username, self.password)


    def test_image_list(self):
        login_system(self.client, self.username, self.password)
        self.client.get("image/image_list")

    def test_image_generator(self):
        login_system(self.client, self.username, self.password)
        self.client.get("image/image_generator")

    def test_launch_instance(self):
        login_system(self.client, self.username, self.password)
        instance_name = "test_launch_instance"
        instance_image_id = "2d9e2df3-a6ce-4c40-9aa4-fdc709beca19"
        instance_flavor_id = "1"
        #############################################
        # launch an instance
        #############################################
        launch_instance_ret = self.client.post("image/launch_instance",
                                               data=dict(launch_imageid=instance_image_id,
                                                         instance_name=instance_name,
                                                         image_flavor=instance_flavor_id))
        launch_instance_result = json.loads(launch_instance_ret.data)
        assert launch_instance_result['status'] == "success"
        #############################################
        # launch an instance while name existed
        #############################################
        launch_instance_existed_ret = self.client.post("image/launch_instance",
                                                       data=dict(launch_imageid=instance_image_id,
                                                                 instance_name=instance_name,
                                                                 image_flavor=instance_flavor_id))
        launch_instance_existed_result = json.loads(launch_instance_existed_ret.data)
        assert launch_instance_existed_result['status'] == "existed"

    def test_delete_instance(self):
        login_system(self.client, self.username, self.password)
        instance_name = "test_delete_instance"
        instance_image_id = "2d9e2df3-a6ce-4c40-9aa4-fdc709beca19"
        instance_flavor_id = "1"
        vm = OpenstackComputeService.create_server(name=instance_name,
                                                   image=instance_image_id,
                                                   flavor=instance_flavor_id)
        self.detect_create_vm_state(instance_name)
        instance = Instance()
        instance.vmid = vm.id
        instance.image = instance_image_id
        instance.flavor = instance_flavor_id
        instance.name = instance_name
        desktop = Desktop()
        desktop.vm_ref = vm.id
        desktop.name = instance_name
        desktop.vm_state = "ACTIVE"
        instance.status = "ACTIVE"
        db.session.add(instance)
        db.session.commit()
        db.session.add(desktop)
        db.session.commit()
        delete_instance_ret = self.client.post("image/delete_instance",
                                          data=dict(vmid=vm.id))
        delete_instance_result = json.loads(delete_instance_ret.data)
        OpenstackComputeService.delete_server(vm)
        assert delete_instance_result['status'] == "success"

    def test_image_instance_list(self):
        login_system(self.client, self.username, self.password)
        instance_name = "test_image_instance_list"
        instance_image_id = "2d9e2df3-a6ce-4c40-9aa4-fdc709beca19"
        instance_flavor_id = "1"
        vm = OpenstackComputeService.create_server(name=instance_name,
                                                   image=instance_image_id,
                                                   flavor=instance_flavor_id)
        self.detect_create_vm_state(instance_name)
        instance = Instance()
        instance.vmid = vm.id
        instance.image = instance_image_id
        instance.flavor = instance_flavor_id
        instance.name = instance_name
        instance.status = "ACTIVE"
        db.session.add(instance)
        db.session.commit()
        self.client.post("image/image_instance_list")
        OpenstackComputeService.delete_server(vm)

    def test_get_instance_console(self):
        """
        This method may be abandoned
        :return:
        """

        login_system(self.client, self.username, self.password)
        instance_name = "test_get_instance_console"
        instance_image_id = "2d9e2df3-a6ce-4c40-9aa4-fdc709beca19"
        instance_flavor_id = "1"
        vm = OpenstackComputeService.create_server(name=instance_name,
                                                   image=instance_image_id,
                                                   flavor=instance_flavor_id)
        self.detect_create_vm_state(instance_name)
        instance = Instance()
        instance.vmid = vm.id
        instance.image = instance_image_id
        instance.flavor = instance_flavor_id
        instance.name = instance_name
        instance.status = "ACTIVE"
        db.session.add(instance)
        db.session.commit()
        #self.client.get("image/get_instance_console?vmid=" + vm.id)
        OpenstackComputeService.delete_server(vm)

    def test_delete_image(self):
        login_system(self.client, self.username, self.password)
        instance_name = "test_delete_image"
        instance_image_id = "2d9e2df3-a6ce-4c40-9aa4-fdc709beca19"
        instance_flavor_id = "1"
        vm = OpenstackComputeService.create_server(name=instance_name,
                                                   image=instance_image_id,
                                                   flavor=instance_flavor_id)
        self.detect_create_vm_state(instance_name)
        instance = Instance()
        instance.vmid = vm.id
        instance.image = instance_image_id
        instance.flavor = instance_flavor_id
        instance.name = instance_name
        desktop = Desktop()
        desktop.vm_ref = vm.id
        desktop.name = instance_name
        desktop.vm_state = "ACTIVE"
        instance.status = "ACTIVE"
        db.session.add(instance)
        db.session.commit()
        db.session.add(desktop)
        db.session.commit()
        ##########################################
        # First, create a snapshot
        ##########################################
        create_new_ret = self.client.post("image/create_snapshot",
                                          data=dict(snapshot_name="unittest",
                                                    create_snapshot_vmid=vm.id))
        create_new_result = json.loads(create_new_ret.data)
        self.detect_create_snapshot_state("unittest")
        OpenstackComputeService.delete_server(vm.id)
        unitest_image = OpenstackImageService.get_image_by_name("unittest")
        ##########################################
        # Then, delete a snapshot
        ##########################################
        del_ret = self.client.post("image/delete_image",
                                          data={"imageIds[]": unitest_image.id})
        del_result = json.loads(del_ret.data)
        assert create_new_result['status'] == "success"
        assert del_result['status'] == "success"

    def test_update_image(self):
        login_system(self.client, self.username, self.password)
        instance_name = "test_update_image"
        instance_image_id = "2d9e2df3-a6ce-4c40-9aa4-fdc709beca19"
        instance_flavor_id = "1"
        vm = OpenstackComputeService.create_server(name=instance_name,
                                                   image=instance_image_id,
                                                   flavor=instance_flavor_id)
        self.detect_create_vm_state(instance_name)
        instance = Instance()
        instance.vmid = vm.id
        instance.image = instance_image_id
        instance.flavor = instance_flavor_id
        instance.name = instance_name
        desktop = Desktop()
        desktop.vm_ref = vm.id
        desktop.name = instance_name
        desktop.vm_state = "ACTIVE"
        instance.status = "ACTIVE"
        db.session.add(instance)
        db.session.commit()
        db.session.add(desktop)
        db.session.commit()
        ##########################################
        # First, create a snapshot
        ##########################################
        create_new_ret = self.client.post("image/create_snapshot",
                                          data=dict(snapshot_name="unittest",
                                                    create_snapshot_vmid=vm.id))
        create_new_result = json.loads(create_new_ret.data)
        assert create_new_result['status'] == 'success'
        self.detect_create_snapshot_state("unittest")
        OpenstackComputeService.start_server(vm.id)
        self.detect_start_vm_state(instance_name)
        ##########################################
        # Then, create another snapshot
        ##########################################
        create_new_ret1 = self.client.post("image/create_snapshot",
                                          data=dict(snapshot_name="unittest1",
                                                    create_snapshot_vmid=vm.id))
        create_new_result1 = json.loads(create_new_ret1.data)
        assert create_new_result1['status'] == 'success'
        self.detect_create_snapshot_state("unittest1")
        unitest_image = OpenstackImageService.get_image_by_name("unittest")
        unitest_image1 = OpenstackImageService.get_image_by_name("unittest1")
        ##########################################
        # Update image with an existed name
        ##########################################
        update_image_dict1 = {"imagename": "unittest1",
                              "imageid": unitest_image.id,
                              "imageformat": 'OVF',
                              "imagevisibility": True}
        update_image_ret1 = self.client.post("image/update_image",
                                             data=update_image_dict1)
        update_image_result1 = json.loads(update_image_ret1.data)
        assert update_image_result1['status'] == 'existed'
        ##########################################
        # Update image with an legal name
        ##########################################
        update_image_dict2 = {"imagename": "unittest2",
                              "imageid": unitest_image.id,
                              "imageformat": 'OVF',
                              "imagevisibility": True }
        update_image_ret2 = self.client.post("image/update_image",
                                             data=update_image_dict2)
        update_image_result2 = json.loads(update_image_ret2.data)
        assert update_image_result2['status'] == 'success'
        ##########################################
        # Clear test environment
        ##########################################
        OpenstackComputeService.delete_server(vm.id)
        unitest_image = OpenstackImageService.get_image_by_name("unittest2")
        OpenstackImageService.delete_image(unitest_image.id)
        OpenstackImageService.delete_image(unitest_image1.id)

    def test_delete_instance(self):
        login_system(self.client, self.username, self.password)
        instance_name = "test_delete_instance"
        instance_image_id = "2d9e2df3-a6ce-4c40-9aa4-fdc709beca19"
        instance_flavor_id = "1"
        vm = OpenstackComputeService.create_server(name=instance_name,
                                                   image=instance_image_id,
                                                   flavor=instance_flavor_id)
        self.detect_create_vm_state(instance_name)
        instance = Instance()
        instance.vmid = vm.id
        instance.image = instance_image_id
        instance.flavor = instance_flavor_id
        instance.name = instance_name
        desktop = Desktop()
        desktop.vm_ref = vm.id
        desktop.name = instance_name
        desktop.vm_state = "ACTIVE"
        instance.status = "ACTIVE"
        db.session.add(instance)
        db.session.commit()
        db.session.add(desktop)
        db.session.commit()
        ret = self.client.post("image/delete_instance",
                               data=dict(vmid=instance.vmid))
        result = json.loads(ret.data)
        assert result['status'] == 'success'
        assert result['vmname'] == instance_name
        OpenstackComputeService.delete_server(vm.id)

    def test_create_snapshot(self):
        login_system(self.client, self.username, self.password)
        instance_name = "test_create_snapshot"
        instance_image_id = "2d9e2df3-a6ce-4c40-9aa4-fdc709beca19"
        instance_flavor_id = "1"
        vm = OpenstackComputeService.create_server(name=instance_name,
                                                   image=instance_image_id,
                                                   flavor=instance_flavor_id)
        self.detect_create_vm_state(instance_name)
        instance = Instance()
        instance.vmid = vm.id
        instance.image = instance_image_id
        instance.flavor = instance_flavor_id
        instance.name = instance_name
        desktop = Desktop()
        desktop.vm_ref = vm.id
        desktop.name = instance_name
        desktop.vm_state = "ACTIVE"
        instance.status = "ACTIVE"
        db.session.add(instance)
        db.session.commit()
        db.session.add(desktop)
        db.session.commit()
        ##########################################
        #  reate a snapshot
        ##########################################
        create_new_ret = self.client.post("image/create_snapshot",
                                          data=dict(snapshot_name="unittest",
                                                    create_snapshot_vmid=vm.id))
        create_new_result = json.loads(create_new_ret.data)
        assert create_new_result['status'] == 'success'
        self.detect_create_snapshot_state("unittest")
        ##########################################
        # Create another name existed snapshot
        ##########################################
        OpenstackComputeService.start_server(vm.id)
        self.detect_start_vm_state(instance_name)
        create_existed_ret = self.client.post("image/create_snapshot",
                                          data=dict(snapshot_name="unittest",
                                                    create_snapshot_vmid=vm.id))
        create_existed_result = json.loads(create_existed_ret.data)
        assert create_existed_result['status'] == 'exist'
        ##########################################
        # Clear test environment
        ##########################################
        OpenstackComputeService.delete_server(vm.id)
        unitest_image = OpenstackImageService.get_image_by_name("unittest")
        OpenstackImageService.delete_image(unitest_image.id)

    def test_power_on(self):
        login_system(self.client, self.username, self.password)
        instance_name = "test_power_on"
        instance_image_id = "2d9e2df3-a6ce-4c40-9aa4-fdc709beca19"
        instance_flavor_id = "1"
        vm = OpenstackComputeService.create_server(name=instance_name,
                                                   image=instance_image_id,
                                                   flavor=instance_flavor_id)
        self.detect_create_vm_state(instance_name)
        OpenstackComputeService.stop_server(vm.id)
        self.detect_stop_vm_state(instance_name)
        instance = Instance()
        instance.vmid = vm.id
        instance.image = instance_image_id
        instance.flavor = instance_flavor_id
        instance.name = instance_name
        instance.status = "SHUTOFF"
        db.session.add(instance)
        db.session.commit()
        power_on__ret = self.client.post("image/power_on",
                                          data=dict(vmid=vm.id))
        power_on_result = json.loads(power_on__ret.data)
        self.detect_start_vm_state(instance_name)
        assert power_on_result['status'] == 'success'
        OpenstackComputeService.delete_server(vm.id)

    def test_power_off(self):
        login_system(self.client, self.username, self.password)
        instance_name = "test_power_off"
        instance_image_id = "2d9e2df3-a6ce-4c40-9aa4-fdc709beca19"
        instance_flavor_id = "1"
        vm = OpenstackComputeService.create_server(name=instance_name,
                                                   image=instance_image_id,
                                                   flavor=instance_flavor_id)
        self.detect_create_vm_state(instance_name)
        instance = Instance()
        instance.vmid = vm.id
        instance.image = instance_image_id
        instance.flavor = instance_flavor_id
        instance.name = instance_name
        instance.status = "ACTIVE"
        db.session.add(instance)
        db.session.commit()
        power_on__ret = self.client.post("image/power_off",
                                          data=dict(vmid=vm.id))
        power_on_result = json.loads(power_on__ret.data)
        self.detect_stop_vm_state(instance_name)
        OpenstackComputeService.delete_server(vm.id)
        assert power_on_result['status'] == 'success'

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
    def detect_create_snapshot_state(snapshot_name):
         while True:
            status = OpenstackImageService.get_image_by_name(snapshot_name).status
            if status == 'queued' or status == 'saving':
                time.sleep(3)
            elif status == 'active':
                break
            else:
                raise ValueError

    @staticmethod
    def detect_start_vm_state(vm_name):
        while True:
            status = OpenstackComputeService.get_server_by_name(vm_name).status
            if status == 'SHUTOFF':
                time.sleep(3)
            elif status == 'ACTIVE':
                break
            else:
                raise ValueError

    @staticmethod
    def detect_stop_vm_state(vm_name):
        while True:
            status = OpenstackComputeService.get_server_by_name(vm_name).status
            if status == 'ACTIVE':
                time.sleep(3)
            elif status == 'SHUTOFF':
                break
            else:
                raise ValueError