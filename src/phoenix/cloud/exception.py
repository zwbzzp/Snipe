# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# Cloud exception
#
# 2016/1/23 lipeizhao: Init


class CloudError(Exception):
    """
    Base exception for all custom cloud exceptions.

    :kwarg inner_exception: an original exception which was wrapped with
        CloudError or its subclasses.
    """

    def __init__(self, inner_exception=None):
        self.inner_exception = inner_exception
        super(CloudError, self).__init__(str(inner_exception))


class CloudConnectionError(CloudError):
    """
    Raised when cloud connection is failed.
    """
    pass


class RetryRequest(Exception):
    """
    Error raised when operation needs to be retried.
    """
    def __init__(self, inner_exc):
        self.inner_exc = inner_exc
