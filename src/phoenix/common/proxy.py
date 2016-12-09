# -*- coding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# Proxy utils
#
# 2016/04/13 fengyingcai: init


class SimpleProxy(object):
    """ A simple proxy

    This proxy only support __getattr__
    """
    def __init__(self, finder):
        self._finder = finder

    def _get_real_obj(self):
        return self._finder()

    def __getattr__(self, name):
        if name == '__members__':
            return dir(self._get_real_obj())
        return getattr(self._get_real_obj(), name)
