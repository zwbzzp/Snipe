# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# Logging module
# This module is compatible with python's logging module
#
# 2016/1/22 fengyc : Init

import logging

import phoenix.config as cfg

logging_options = [
    cfg.StrOpt('log_file', default='stderr',
               help='Logging file, stdout for standard out, stderr for standard error')
]

# Log levels
DEBUG = logging.DEBUG
INFO = logging.INFO
WARNING = logging.WARNING
ERROR = logging.ERROR


def getLevelName(level):
    """ Get log level name
    :param level: log level
    :return: predefined level name, or 'Level %level'
    """
    return logging.getLevelName(level)


def debug(message):
    return log(DEBUG, message=message)


def info(message):
    return log(INFO, message=message)


def warning(message):
    return log(WARNING, message=message)


def error(message):
    return log(ERROR, message=message)


def log(level, message):
    raise NotImplementedError



