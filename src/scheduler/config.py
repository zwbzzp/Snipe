# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# Config
#
# 2016/2/17 fengyc : Init


class Config(object):
    # celery broker
    BROKER_URL = 'amqp://root:admin123@127.0.0.1:5672//'


class DebugConfig(Config):
    pass


class TestConfig(Config):
    pass


class ProductConfig(Config):
    pass


config = {
    'debug': DebugConfig,
    'test': TestConfig,
    'product': ProductConfig,

    'default': ProductConfig,
}
