# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# Desktop module
#
# 2016/1/22 fengyc : Init

from phoenix.common.singleton import LocalSingletonMixin


class DesktopManager(LocalSingletonMixin):
    """ Desktop manager.
    """
    def __init__(self, *args, **kwargs):
        pass

    def create(self, context, *args, **kwargs):
        pass

    def destroy(self, context, *args, **kwargs):
        pass

    def suspend(self, context, *args, **kwargs):
        pass

    def resume(self, context, *args, **kwargs):
        pass

    def power_on(self, context, *args, **kwargs):
        pass

    def power_off(self, context, *args, **kwargs):
        pass

    def rescue(self, context, *args, **kwargs):
        pass

    def unrescue(self, context, *args, **kwargs):
        pass

    def rebuild(self, context, *args, **kwargs):
        pass


class PoolManager(LocalSingletonMixin):
    """ Pool manager.
    """
    def __init__(self):
        pass

    def create(self, context, image_id, network_id, flavor_id, *args, **kwargs):
        pass

    def destroy(self, context, *args, **kwargs):
        pass

    def update(self, context, *args, **kwargs):
        pass

    def list(self, context, *args, **kwargs):
        """ List pools
        :param context:
        :param args:
        :param kwargs:
        :return:
        """
        pass

