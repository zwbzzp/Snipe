# -*- encoding: utf-8 -*-
# Copyright Vinzor Co.,Ltd.
#
# Time utility functions
#
# 20161114 fengyingcai: Init

import datetime
import pytz
import tzlocal
import iso8601

# UTC timezone
UTC = pytz.utc

# LOCAL timezone
LOCAL = tzlocal.get_localzone()

# All timezones supported in pytz
ALL_TZ_NAMES = pytz.all_timezones


def tz_from_name(tzname):
    """ Convert timezone name to timezone
    :param tzname: name
    :type tzname: str
    :return: timezone
    :rtype: datetime.tzinfo
    """
    return pytz.timezone(tzname)


def tz_to_name(tz):
    """ Convert timezone to name
    :param tz: timezone, which should be generate from timeutils module
    :type tz: datetime.tzinfo
    :return: name of timezone
    :rtype: str
    """
    return tz.zone


def tznow(tz=None):
    """ Timezone now
    :param tz: timezone, default is local
    :type tz: datetime.tzinfo
    :return: Time of tz
    :rtype: datetime.datetime
    """
    if tz is None:
        tz = LOCAL
    return datetime.datetime.now(tz)

now = tznow


def utcnow():
    """ UTC now
    :return: Time of utc
    :rtype: datetime.datetime
    """
    return tznow(UTC)


def is_offset_naive(dt):
    """ Check whether datetime contain timezone info
    :param dt: datetime
    :type dt: datetime.datetime
    :return: True if dt is offset-naive, else False
    :rtype: bool
    """
    return dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None


def convert_to_tz(dt, tz=None):
    """ Convert a datetime to other timezone
    :param dt: datetime, treat it as utc if datetime is offset-naive
    :type dt: datetime.datetime
    :param tz: timezone, default is utc
    :type tz: datetime.tzinfo
    :return: datetime in tz
    :rtype: datetime.datetime
    """
    if is_offset_naive(dt):
        dt.replace(tzinfo=UTC)
    if tz is None:
        tz = UTC
    return dt.astimezone(tz=tz)


def to_iso8601(dt):
    """Convert a datetime object to iso8601 format string

    :param dt: datetime
    :type dt: datetime.datetime
    """
    return dt.isoformat()


def from_iso8601(s, tz=None):
    """Convert a iso8601 format string to a datetime object

    :param s: iso8601 format string
    :param tz: default timezone of datetime, if timezone info not exists in s
    :rtype: datetime.datetime
    """
    return iso8601.parse_date(s, default_timezone=tz)


def get_week_start_date(date):
    """Get week start date of the date or datetime"""
    weekday = date.weekday()
    return date - datetime.timedelta(days=weekday)


def get_week_end_date(date):
    """Get week end date of the date or datetime"""
    return get_week_start_date(date) + datetime.timedelta(days=6)


def to_time(s, format='%H:%M'):
    """Convert a time string to time object according to the given format."""
    return datetime.datetime.strptime(s, format).time()


def format_time(t, format='%H:%M'):
    """Convert a time object to a string"""
    return t.strftime(format)


def to_datetime(s, format='%Y-%m-%d %H:%M'):
    """Convert a string to a datetime object"""
    return datetime.datetime.strptime(s, format)


def format_datetime(dt, format='%Y-%m-%d %H:%M'):
    """Convert a datetime object to a string"""
    return dt.strftime(format)