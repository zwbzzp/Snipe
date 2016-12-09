# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# comment
#
# 2016/2/26 fengyc : Init

import os, sys

basedir = os.path.abspath(os.path.dirname(__file__))
sys.path.append(basedir)
sys.path.append(os.path.join(basedir, '..'))

from .test_basics import BasicsTestCase
from .test_celery import CeleryTest
from .test_desktop import DesktopTest
from .test_image import ImageTest
from .test_log import LogTest
from .test_openstack import NovaTest
from .test_setting import SettingTest
from .test_storage import StorageTest
from .test_edu import EduTest
