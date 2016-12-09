# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# scheduler module
#
# 20160121 fengyingcai : Init

from celery import Celery
from config import config


def create_celery(config_name='default'):
    app = Celery()

    app.config_from_object(config[config_name])

    return app
