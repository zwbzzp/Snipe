# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# comment
#
# 2016/4/21 qinjinghui : Init
__author__ = 'qinjinghui'


from base import FlaskTest
from flask import json, jsonify
from app import app, db



class SettingTest(FlaskTest):

    def setUp(self):
        super(SettingTest, self).setUp()
        self.app.config['WTF_CSRF_ENABLED'] = False

    def test_add_flavor(self):
        #from web.manage import test_setup
        #test_setup()

        name="123"
        ramnum=2048
        cpunum=2
        disknum=60
        add_ret = self.app.test_client().post('/setting/add_flavor',
                           data=dict(name=name, ramnum=ramnum,
                                     cpunum=cpunum, disknum=disknum))
        #ret = self.app.test_client().get('/setting/flavor',follow_redirects=True)
        add_result = json.loads(add_ret.data)

        ids =[]
        from phoenix.cloud import compute as OpenstackComputeService
        flavor_list = OpenstackComputeService.list_flavors()
        for flavor in flavor_list:
            if flavor.name == name:
                ids.append(flavor.id)
                break
        del_ret = self.app.test_client().post('/setting/delete_flavor', data={"ids[]":ids})
        del_result = json.loads(del_ret.data)
        assert add_result['status'] == 'success'
        assert del_result['status'] == 'success'

    def test_update_flavor(self):
        flavor1 = {"name":"123","ramnum":2048,"cpunum":2,"disknum":60}
        flavor2 = {"name":"234","ramnum":2048,"cpunum":2,"disknum":60}
        add_ret1 = self.app.test_client().post('/setting/add_flavor',
                           data=flavor1)
        add_result1 = json.loads(add_ret1.data)
        add_ret2 = self.app.test_client().post('/setting/add_flavor',
                           data=flavor2)
        add_result2 = json.loads(add_ret2.data)

        from phoenix.cloud import compute as OpenstackComputeService
        flavor_list = OpenstackComputeService.list_flavors()
        flavor1_id = None
        for flavor in flavor_list:
            if flavor.name == flavor1["name"] :
                flavor1_id = flavor.id
        edit_flavor_dict1 = {"flavorid": flavor1_id, "name": "234","ramnum":2048,"cpunum":2,"disknum":60}
        update_ret1 = self.app.test_client().post('/setting/update_flavor',
                                                 data=edit_flavor_dict1)
        update_result1 = json.loads(update_ret1.data)

        edit_flavor_dict2 = {"flavorid": flavor1_id, "name": "123","ramnum":2048,"cpunum":3,"disknum":60}
        update_ret2 = self.app.test_client().post('/setting/update_flavor',
                                                 data=edit_flavor_dict2)
        update_result2 = json.loads(update_ret2.data)

        ids =[]
        from phoenix.cloud import compute as OpenstackComputeService
        flavor_list = OpenstackComputeService.list_flavors()
        for flavor in flavor_list:
            if flavor.name == flavor1["name"] or flavor.name == flavor2["name"]:
                ids.append(flavor.id)
        del_ret = self.app.test_client().post('/setting/delete_flavor', data={"ids[]":ids})
        del_result = json.loads(del_ret.data)
        assert add_result1['status'] == 'success'
        assert add_result2['status'] == 'success'
        assert update_result1['status'] == 'existed'
        assert update_result2['status'] == 'success'
        assert del_result['status'] == 'success'

    def test_delete_flavor(self):
        name = "123"
        ramnum = 2048
        cpunum = 2
        disknum = 60
        add_ret = self.app.test_client().post('/setting/add_flavor',
                           data=dict(name=name, ramnum=ramnum,
                                     cpunum=cpunum, disknum=disknum))
        #ret = self.app.test_client().get('/setting/flavor',follow_redirects=True)
        add_result = json.loads(add_ret.data)


        ids =[]
        from phoenix.cloud import compute as OpenstackComputeService
        flavor_list = OpenstackComputeService.list_flavors()
        for flavor in flavor_list:
            if flavor.name == name:
                ids.append(flavor.id)
                break
        del_ret = self.app.test_client().post('/setting/delete_flavor', data={"ids[]":ids})
        del_result = json.loads(del_ret.data)
        assert add_result['status'] == 'success'
        assert del_result['status'] == 'success'


