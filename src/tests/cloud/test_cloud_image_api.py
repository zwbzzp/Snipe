# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# cloud api unit tests
#
# 20160113 lipeizhao : Init

from tests import test
from tests import fixture as db_fixtures

from phoenix.cloud import image


class ImageTestCase(test.TestCase):

    def setUp(self):
        super(ImageTestCase, self).setUp()
        self.ctxt = None

    def test_list_image(self):
        size = 20
        results = image.list_images(page_size=size)
        self.assertIsNotNone(results)

    def test_get_image(self):
        result = image.create_image(name='test_image_name_1',
                                    visibility='public',
                                    description='fake desc')
        result_get = image.get_image(result.id)
        result_get_by_name = image.get_image_by_name(result.name)
        self.assertEqual(result.id, result_get.id)
        self.assertEqual(result.name, result_get_by_name.name)

    def test_create_image(self):
        pass

    def test_delete_image(self):
        result = image.create_image(name='test_image_name_2',
                                    visibility='public',
                                    description='fake desc')
        image.delete_image(result.id)
        images = image.list_images()
        found_flag = False
        for img in images:
            if img.id == result.id:
                found_flag = True
        self.assertEqual(found_flag, False)

    def tearDown(self):
        super(ImageTestCase, self).tearDown()
        images = image.list_images()
        for img in images:
            if img.name.find('test_image') == 0:
                image.delete_image(img.id)


