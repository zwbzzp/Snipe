# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# exceptions
#
# 2016/2/1 fengyc : Init


class BaseException(Exception):
    def __int__(self, *args, **kwargs):
        super(BaseException, self).__int__(*args, **kwargs)


class ConfigException(BaseException):
    pass