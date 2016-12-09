# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# comment
#
# 2016/2/18 lipeizhao : Init

import datetime

from sqlalchemy import and_, cast, \
    Integer, or_, not_

from ..models import Lesson,Course, Period
from ..license.utils import LicenseUtils

# init license utils
license = LicenseUtils()


def get_week_period_info_detail(start_date, user):
    """get the period resource usage detail of the week"""
    detail_table = {}
    week_lessons = []
    end_date = start_date + datetime.timedelta(7)
    periods = Period.query.order_by(Period.start_time).all()
    if user.role.name == "Administrator":
        week_lessons = Lesson.query.filter(
            not_(or_(Lesson.start_date > end_date, Lesson.end_date < start_date))
        ).all()
    elif user.role.name == "Teacher":
        course_teacher = Course.query.filter_by( owner_id = user.id ).all()
        for course_t in course_teacher:
            lessons_teacher = Lesson.query.filter_by( course_id = course_t.id)
            week_teacher_lessons = lessons_teacher.filter(
                not_(or_(Lesson.start_date > end_date, Lesson.end_date < start_date))
            ).all()
            week_lessons.extend(week_teacher_lessons)
    elif user.role.name == "Student":
        lesson_all = Lesson.query.filter(
            not_(or_(Lesson.start_date > end_date, Lesson.end_date < start_date))
        ).all()
        for lesson in lesson_all:
            course_student = Course.query.filter_by( id = lesson.course_id ).first()
            student = course_student.users.filter_by( id = user.id ).first()
            if student :
                week_lessons.append(lesson)
    for i in range(0, 7):
        day = start_date + datetime.timedelta(days=i)
        for period in periods:
            start_datetime = datetime.datetime.combine(day, period.start_time)
            end_datetime = datetime.datetime.combine(day, period.end_time)
            lessons = [lesson for lesson in week_lessons
                      if not (lesson.end_datetime <= start_datetime or
                      lesson.start_datetime >= end_datetime)]
            # calculate the vm count and get the level of resource usage
            vm_count = 0
            course_detail_list = {}
            course_detail = ''
            for le in lessons:
                course = le.course
                if not course:
                    continue
                capacity = course.capacity if course.capacity else 0
                vm_count += capacity

                if not course_detail_list.get(course.name, None):
                    course_detail_list[course.name] = {'vm_count': capacity}
                else:
                    course_detail_list[course.name]['vm_count'] += capacity
            usage_level = _get_resource_usage_level(vm_count)
            table_item = {'vm_count': vm_count,
                          'course_detail_list': course_detail_list,
                          'usage_level': usage_level}
            if not detail_table.get(period.id, None):
                detail_table[period.id] = {}
            detail_table[period.id][i + 1] = table_item
    return detail_table

def _get_resource_usage_level(vm_count):
    """return the resource usage level according to the given parameters"""
    # TODO: should consider vm RAM and cpu number instead
    license_info = license.get_license_info()
    vm_limitation = int(license_info[0])

    percentage = vm_count / vm_limitation
    level = 0
    if percentage <= 0:
        level = 0
    elif percentage <=0.3:
        level = 1
    elif percentage <= 0.6:
        level = 6
    elif percentage <= 0.9:
        level = 9
    else:
        level = 10
    return str(level)

# if __name__ == '__main__':
#     from datetime import date, datetime, time
#     day = datetime(2016, 3, 11)
#     lession = Lesson.query.filter(Lesson.date == day).all()