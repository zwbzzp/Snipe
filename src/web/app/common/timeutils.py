# -*- encoding: utf-8 -*-
# Copyright Vinzor Co.,Ltd.
#
# Time utility functions for web app
#
# 20161114 lipeizhao: Init

import datetime
import time


def get_week_start_date(date):
    weekday = date.weekday()
    return date - datetime.timedelta(days=weekday)


def get_week_end_date(date):
    return get_week_start_date(date) + datetime.timedelta(days=6)


def time_format(value, format='%H:%M'):
    """Formats a time according to the given format."""
    if value in (None, ''):
        return ''
    try:
        return datetime.datetime.strptime(value, format).time()
    except AttributeError as ex:
        return ''


def datetime_format(value, format='yyyy-MM-dd HH:mm'):
    """Formats a date time according to the given format."""
    if value in (None, '') and not isinstance(value, datetime.datetime):
        return ''
    try:
        return value.strftime(format)
    except AttributeError as ex:
        return ''


def str_to_time(str_time, format='%H:%M'):
    """ Convert a time
    :param str_time:
    :param format:
    :return:
    """
    return datetime.datetime.strptime(str_time, format).time()

def now():
    today = datetime.date.today()
    return today