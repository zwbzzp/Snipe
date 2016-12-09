# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# comment
#
# 2016/3/19 lipeizhao : Init
# 2016/6/21 fengyingcai: 对时间表进行排序,解决序号与时段排序不一致问题

import datetime
import subprocess
import os
import rsa
from random import randint, choice
import string
import logging
import hashlib
from binascii import hexlify,unhexlify

from voluptuous import Schema, Required, All, Length, Range, Invalid
from sqlalchemy import and_, cast, \
    Integer
import requests
import shutil

LOG = logging.getLogger(__name__)

def is_timetable_legal(timetable):
    """判断时间表是否合法
    "   合法条件: 每一节课的开始时间和结束时间不能为空，且每个时间点的设置都是递增的
    :rtype: object
    """
    last_time = "00:00"
    last_time = int(last_time.replace(":",""))
    values = [x for x in timetable.values()]
    values = sorted(values, key=lambda x: int(x['start_time'].replace(':', '')))

    for value in values:
        start_time = int(value["start_time"].replace(":",""))
        end_time = int(value["end_time"].replace(":",""))
        if start_time and end_time and start_time >= last_time and end_time > start_time:
            last_time = end_time
        else:
            return False
    return True

def check_time_conflict(start_time, end_time, periods):
    periods = sorted(periods, key=lambda x: x.start_time)
    for period in periods:
        if not (end_time <= period.start_time or start_time >= period.end_time):
            return False
    return True

class ParametersValidator():

    # define parameter validators here
    def __init__(self):
        self.schema = Schema({
            'param_1': All(str, Length(min=5)),
            'param_2': All(self.Int()),
            'param_3': All(self.Date())
        })

    def validate(self, parameters):
        fail_dict = {}
        for key in parameters:
            try:
                self.schema({key: parameters[key]})
            except Invalid as e:
                fail_dict[key] = {'value': parameters[key],
                                  'msg': e.msg}
        return fail_dict

    # helper methods
    def Date(self, fmt='%Y/%m/%d'):
        return lambda v: datetime.datetime.strptime(v, fmt)

    def Int(self):
        def is_int(v):
            try:
                int(v)
            except Exception as e:
                raise Invalid('not int')
        return is_int


ParamsValidator = ParametersValidator()


def judge_file(file, size):
    '''
    To judge whether the file is valid.
    @param file: the file object
    @param size: the size(MB) of the limit of the file.
    '''
    try:
        if file and size:
            if file.content_length > (size * 1024 * 1024):
                return False, "too large"
            temp = file.filename.split(".")
            file_type = temp[len(temp) - 1]
            if file_type == "xls" or file_type == "xlsx":
                return True, ""
            else:
                return False,"type error"
        else:
            raise "Invalid parameter"
    except Exception as ex:
        LOG.exception("Check File Failed: %s", ex)
        return False, ""


if __name__ == '__main__':
    pass