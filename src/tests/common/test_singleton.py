# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# comment
#
# 2016/1/26 fengyc : Init

import unittest
import threading

from phoenix.common.singleton import LocalSingletonMixin


class A(LocalSingletonMixin):
    pass


a = None
b = None


def create_a():
    global a
    a = A()


def create_b():
    global b
    b = A()


class SingletonTest(unittest.TestCase):
    def setUp(self):
        pass

    def test_local_singleton_mixin(self):
        thread_a = threading.Thread(target=create_a)
        thread_a.start()
        thread_b = threading.Thread(target=create_b)
        thread_b.start()
        thread_a.join()
        thread_b.join()

        self.assertNotEqual(a, b)


if __name__ == '__main__':
    unittest.main()