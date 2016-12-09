# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# comment
#
# 2016/4/20 0020 Jay : Init

import datetime
from sqlalchemy import not_, and_, or_
from app import db
from ...common.timeutils import get_week_end_date, get_week_start_date
from ...models import Period, Lesson


def get_this_week_start_and_end_date():
    today = datetime.date.today()
    return (get_week_start_date(today), get_week_end_date(today))


def get_date_from_weekday(course, start_weekday, end_weekday):
    """
    获得最靠近课程开始时间且符合对应天数的开始日期和结束日期
    :param course:
    :param start_weekday: 0 - 6 周一到周日
    :param end_weekday:  0 - 6 周一到周日
    :return: 开始日期与结束日期的元组
    """
    day_delta = (start_weekday - course.start_date.weekday() + 7) % 7
    start_current_date = course.start_date + datetime.timedelta(day_delta)
    end_current_date = start_current_date + datetime.timedelta(end_weekday - start_weekday)
    return (start_current_date, end_current_date)


def next_day(date):
    """
    计算明天的日期
    """
    return date + datetime.timedelta(1)


def next_week(date):
    """
    计算下星期同一天的日期
    """
    return date + datetime.timedelta(7)


def validate_lesson(course, lesson, existed_lessons):
    """
    检验上课时间的合法性
    """
    # 检验上课时间本身的合法性
    if lesson.start_datetime >= lesson.end_datetime:
        return False, "上课开始时间大于结束时间"

    # 检验上课时间是否超出课程时间
    course_start_datetime = \
        datetime.datetime.combine(course.start_date, datetime.time.min)
    course_end_datetime = \
        datetime.datetime.combine(course.end_date, datetime.time.max)
    if not (lesson.start_datetime >= course_start_datetime and
                lesson.end_datetime <= course_end_datetime):
        return False, "上课时间超出课程开设时间"

    for les in existed_lessons:
        # TODO 此处的"="号是否需要？
        if not (lesson.end_datetime <= les.start_datetime or
                    lesson.start_datetime >= les.end_datetime):
            return False, "上课时间与已有的时间段冲突"

    # FIXME 进行数据库检查

    return True, "上课时间添加成功"


def get_timetable_of_this_week(course):
    """
    获得本周课程表
    :param course: 课程
    :return: 是一个列表，列表每一项为一个二元组(period对象, ["状态列表"])
    状态列表共有七项，分别代表星期一到星期六，其值为bool型
    例如：timetable[2][1][3] == False 代表 星期三的时候对应的Period没有安排课
    """
    start_date, end_date = get_this_week_start_and_end_date()
    lessons = course.lessons.filter(
        not_(or_(Lesson.start_date > end_date, Lesson.end_date < start_date))
    ).all()
    periods = Period.query.order_by(Period.start_time).all()
    timetable = []
    for period in periods:
        table = []
        current_date = start_date
        while current_date <= end_date:
            start_datetime = datetime.datetime.combine(current_date, period.start_time)
            end_datetime = datetime.datetime.combine(current_date, period.end_time)
            result = [lesson for lesson in lessons
                      if not (lesson.end_datetime <= start_datetime or
                      lesson.start_datetime >= end_datetime)]
            table.append(True if result else False)
            current_date = next_day(current_date)
        timetable.append((period, table))
    return timetable