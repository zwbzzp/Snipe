# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# Jinja2 filter
#
# 2016/3/14  lipeizhao: Init

from babel import dates


def datetime_format(value, format='yyyy-MM-dd HH:mm'):
    """Formats a date time according to the given format."""
    if value in (None, ''):
        return ''
    try:
        return dates.format_datetime(value, format)
    except AttributeError as ex:
        return ''


def date_format(value, format='yyyy-MM-dd'):
    """Formats a date according to the given format."""
    if value in (None, ''):
        return ''
    try:
        return dates.format_date(value, format)
    except AttributeError as ex:
        return ''


def time_format(value, format='HH:mm'):
    """Formate a datetime.datetime or datetime.time to the given format"""
    if value in (None, ''):
        return ''
    try:
        return dates.format_time(value, format)
    except AttributeError as ex:
        return ''


def filesizeformat(value, binary=False):
    """Format the value like a 'human-readable' file size (i.e. 13 kB,
    4.1 MB, 102 Bytes, etc).  Per default decimal prefixes are used (Mega,
    Giga, etc.), if the second parameter is set to `True` the binary
    prefixes are used (Mebi, Gibi).
    """
    bytes = float(value)
    base = binary and 1024 or 1000
    prefixes = [
        (binary and 'KiB' or 'kB'),
        (binary and 'MiB' or 'MB'),
        (binary and 'GiB' or 'GB'),
        (binary and 'TiB' or 'TB'),
        (binary and 'PiB' or 'PB'),
        (binary and 'EiB' or 'EB'),
        (binary and 'ZiB' or 'ZB'),
        (binary and 'YiB' or 'YB')
    ]
    if bytes == 1:
        return '1 Byte'
    elif bytes < base:
        return '%d Bytes' % bytes
    else:
        for i, prefix in enumerate(prefixes):
            unit = base ** (i + 2)
            if bytes < unit:
                return '%.1f %s' % ((base * bytes / unit), prefix)
        return '%.1f %s' % ((base * bytes / unit), prefix)


if __name__ == '__main__':
    from datetime import date, datetime, time
    tmp = datetime(2017, 4, 1, 15, 30)
    tmp2 = datetime_format(tmp, 'hh:mm')