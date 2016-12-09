# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# comment
#
# 2016/4/14 chengkang : Init

from ..models import UserActionLog, SystemRunningLog
from .. import db
import logging
import traceback
import time, datetime

class UserActionLogger(object):

    def _log(self, user, message, level="info", rollback=False):
        """
        Save the users' action log.

        @param user: The :class:`User` of this action
        @param message: The message<type: str> of this action
        @param level: the level of the log
        @param rollback: roll back the transaction before or not.
        """
        try:
            if rollback:
                # roll back the transaction before
                db.session.rollback()
            # first instore the log to database
            log = UserActionLog(userid=user.username, message=message, level=level.upper())
            db.session.add(log)
            db.session.commit()
            # second instore the log to file
            useraction_logger = logging.getLogger("UserAction")
            if not hasattr(useraction_logger, level):
                raise Exception("log level unexist")
            else:
                getattr(useraction_logger, level)("User[%s]: %s" % (user.username, message))
        except:
            traceback.print_exc()

    def debug(self, user, message, rollback=False):
        self._log(user, message, level="debug", rollback=rollback)

    def info(self, user, message, rollback=False):
        self._log(user, message, level="info", rollback=rollback)

    def error(self, user, message, rollback=False):
        self._log(user, message, level="error", rollback=rollback)


class SystemRunningLogger(object):

    def _log(self, message, level="info", rollback=False):
        """
        Save the system's running log.

        @param message: The message<type: str> of this action
        @param level: the level of the log
        @param rollback: roll back the transaction before or not.
        """
        try:
            if rollback:
                # roll back the transaction before
                db.session.rollback()
            # first instore the log to database
            log = SystemRunningLog(message=message, level=level.upper())
            db.session.add(log)
            db.session.commit()
            # second instore the log to file
            systemrunning_logger = logging.getLogger("SystemRunning")
            if not hasattr(systemrunning_logger, level):
                raise Exception("log level unexist")
            else:
                getattr(systemrunning_logger, level)(message)
        except:
            traceback.print_exc()

    def debug(self, message, rollback=False):
        self._log(message, level="debug", rollback=rollback)

    def info(self, message, rollback=False):
        self._log(message, level="info", rollback=rollback)

    def error(self, message, rollback=False):
        self._log(message, level="error", rollback=rollback)


def parse_date_range(date_range):
    """处理用户操作日志查询的日期选择范围

    @param date_range: 格式为: mm/dd/yyyy - mm/dd/yyyy， 当date_range为空时返回当天的日期
    """
    start_dt, end_dt = None, None
    oneday = datetime.timedelta(days=1)
    if date_range:
        try:
            items = date_range.split('-')
            start_date_str = items[0].strip()
            start_time = time.strptime(start_date_str, "%m/%d/%Y")
            start_dt = datetime.datetime(* start_time[:6])

            end_date_str = items[1].strip()
            end_time = time.strptime(end_date_str, "%m/%d/%Y")
            end_dt = datetime.datetime(* end_time[:6])
            end_dt += oneday
        except:
            traceback.print_exc()
    else:
        today = datetime.date.today()
        start_dt = datetime.datetime(year=today.year, month=today.month, day=today.day)
        end_dt = start_dt + oneday
    return (start_dt, end_dt)
