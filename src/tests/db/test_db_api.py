# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# database unit tests
#
# 20160113 bitson : Init

from tests import test
from tests import fixture as db_fixtures

from phoenix.db import models
from phoenix import db


class UserTestCase(test.TestCase):

    def setUp(self):
        super(UserTestCase, self).setUp()
        self.ctxt = None

    def _get_base_values(self):
        return {
            'name': 'fake_name',
            'password': 'fake_password',
            'email': 'fake',
            'active': True
            }

    def _create_user(self, values):
        v = self._get_base_values()
        v.update(values)
        return db.create_user(self.ctxt, v)

    def test_get_all_users(self):
        pass

    def test_get_user_by_id(self):
        pass

    def test_create_user(self):
        user = self._create_user({})
        self.assertIsNotNone(user['id'])
        for key, value in self._get_base_values().items():
            self.assertEqual(value, user[key])

    def test_user_delete(self):
        pass

