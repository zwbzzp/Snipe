# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# Setting module
#
# Setting module manage runtime setting of phoenix
#
# 2016/1/26 fengyc : Init

from phoenix.common.singleton import LocalSingletonMixin


class CloudSetting(LocalSingletonMixin):

    __group = 'cloud'

    def __init__(self):
        pass

    @property
    def backend_driver(self):
        return 'OpenStack'

    @backend_driver.setter
    def set_backend_driver(self):
        raise NotImplementedError

    @property
    def endpoint(self):
        pass

    @endpoint.setter
    def set_endpoint(self):
        pass

    @property
    def endpoint_params(self):
        pass

    @endpoint_params.setter
    def set_endpoint_params(self, values):
        pass

