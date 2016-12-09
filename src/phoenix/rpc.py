# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# RPC
#
# 2016/1/23 fengyc : Init


def call(context, endpoint, *args, **kwargs):
    """ Call and wait for return
    :param context:
    :param endpoint:
    :param args:
    :param kwargs:
    :return:
    """
    raise NotImplementedError


def async_call(context, endpoint, callback, *args, **kwargs):
    """ Async call and callback
    :param context:
    :param endpoint:
    :param callback:
    :param args:
    :param kwargs:
    :return:
    """
    raise NotImplementedError


def cast(context, endpoint, *args, **kwargs):
    """ Call without callback
    :param context:
    :param endpoint:
    :param args:
    :param kwargs:
    :return:
    """
    raise NotImplementedError