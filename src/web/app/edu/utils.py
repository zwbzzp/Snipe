# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# comment
#
# 2016/4/20 0020 Jay : Init

import datetime
from sqlalchemy import not_, and_, or_
from app import db
from ..common.timeutils import get_week_end_date, get_week_start_date
from ..models import Period, Lesson, Course
from ..common import timeutils


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

def get_timetable_of_given_week(course, start_date_str):
    """
    获得本周课程表
    :param course: 课程
    :return: 是一个列表，列表每一项为一个二元组(period对象, ["状态列表"])
    状态列表共有七项，分别代表星期一到星期六，其值为bool型
    例如：timetable[2][1][3] == False 代表 星期三的时候对应的Period没有安排课
    """
    date = None
    date = datetime.datetime.strptime(start_date_str, '%Y-%m-%d').date()
    start_date = timeutils.get_week_start_date(date)
    end_date = timeutils.get_week_end_date(date)
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

def redefine_all_lessons(course):
    lessons = Lesson.query.filter_by(course_id=course.id).all()
    lessons_list = []
    ischanged = True
    if len(lessons) > 0:
        for lesson in lessons:
            if lesson.start_period is not None and lesson.end_period is not None:
                lessons_list.append(lesson)
    if len(lessons_list) > 0:
        while ischanged:
            ischanged = False
            for lesson in lessons_list:
                end_period_id = lesson.end_period.name
                max_period = 1
                for period in Period.query.all():
                    if int(period.name) > max_period:
                        max_period = int(period.name)
                if end_period_id == str(max_period):
                    next_period_id = end_period_id
                    next_start_date = lesson.end_date
                    end_datetime = datetime.datetime.combine(next_start_date,
                                                             Period.query.filter_by(name=next_period_id).first().end_time)
                else:
                    next_period_id = str(int(end_period_id) + 1)
                    next_start_date = lesson.start_date
                    end_datetime = datetime.datetime.combine(next_start_date,
                                                             Period.query.filter_by(name=next_period_id).first().start_time)
                for i in lessons_list:
                    lesson_start_datetime = datetime.datetime.combine(i.start_date, i.start_time)
                    if end_datetime == lesson_start_datetime:
                        lessons_list.remove(lesson)
                        lessons_list.remove(i)
                        new_lesson = Lesson(course_id=course.id, start_date=lesson.start_date, end_date=i.end_date,
                                            start_time=lesson.start_time,
                                            end_time=i.end_time)
                        new_lesson.start_period = lesson.start_period
                        new_lesson.end_period = i.end_period
                        lessons_list.append(new_lesson)
                        ischanged = True
            for old_lesson in Lesson.query.filter_by(course_id=course.id).all():
                if old_lesson.start_period is not None and old_lesson.end_period is not None:
                    lesson = Lesson.query.filter_by(id=old_lesson.id).first()
                    db.session.delete(lesson)
            for new_lesson in lessons_list:
                lesson = Lesson(course_id=course.id, start_date=new_lesson.start_date, end_date=new_lesson.end_date,
                                start_time=new_lesson.start_time,
                                end_time=new_lesson.end_time)
                lesson.start_period = new_lesson.start_period
                lesson.end_period = new_lesson.end_period
                db.session.add(lesson)
            db.session.add(course)
            db.session.commit()
