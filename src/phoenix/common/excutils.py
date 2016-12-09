# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# Exception utils
#
# 2016/1/25 lipeizhao: Init


import logging
import sys
import traceback


class save_and_reraise_exception(object):
    """
    Save current exception, run some code and then re-raise.
    """
    def __init__(self, reraise=True, logger=None):
        self.reraise = reraise
        if logger is None:
            logger = logging.getLogger()
        self.logger = logger

    def __enter__(self):
        self.type_, self.value, self.tb, = sys.exc_info()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            if self.reraise:
                self.logger.error('Original exception being dropped: %s',
                                  traceback.format_exception(self.type_, self.value, self.tb))
            return False
        if self.reraise:
            reraise(self.type_, self.value, self.tb)


def reraise(tp, value, tb=None):
    if value is None:
        value = tp()
    if value.__traceback__ is not tb:
        raise value.with_traceback(tb)
    raise value

