# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# comment
#
# 2016/2/18 fengyc : Init

import os
import datetime
import logging
from flask import render_template, url_for, request, jsonify, abort, redirect, \
    current_app, send_from_directory, flash, session
from flask.ext.login import login_required, current_user
from sqlalchemy import or_, and_, not_
from sqlalchemy.exc import IntegrityError

import xlrd

from phoenix.common import timeutils

from ..log.utils import UserActionLogger
from ...audit import ResourceController
from . import edu
from .forms import CourseForm, UploadStudentFileForm, CustomizedLessonForm, StudentListForm, \
    TempLessonForm, LessonForm, default_of_protocol
from .utils import get_date_from_weekday, next_day, next_week, validate_lesson, \
    get_this_week_start_and_end_date, get_timetable_of_this_week

from ...models import Period, Course, Role, User, Lesson, Place, Desktop, DesktopType, Protocol, \
    DesktopType, FtpAccount, Image
from ... import db, csrf
from phoenix.cloud import image as OpenstackImageService
from ...common import imageutils

LOG = logging.getLogger(__name__)
ua_logger = UserActionLogger()

@edu.route('/courses', methods=['GET'])
@login_required
def courses():
    # other students
    courses = current_user.courses
    for c in courses:
        # any lesson is running?
        now = datetime.datetime.now()
        c.lesson_now = c.find_current_lesson(now)
    return render_template('students/edu/courses.html', courses=courses)


@edu.route('/check_course_state/<int:id>', methods=['GET'])
@login_required
def check_course_state(id):
    result = {
        'status':'',
        'data': {
            'course_id':id,
            'name':'',
            'capacity':0,
            'desktop_count':0
        }
    }
    course = Course.query.filter_by(id=id).first()
    if course:
        desktop_count = course.desktops.count()
        result['data']['desktop_count'] = desktop_count
        result['data']['name'] = course.name
        result['data']['capacity'] = course.capacity

        now = datetime.datetime.now()
        current_lesson = course.find_current_lesson()

        ######################################
        # There are 3 status of the course:
        # "start": the course already started, two conditions must be met
        #          1. course has current lesson
        #          2. course desktops met the course capacity and all desktops are in active and using status
        # "stop": the course already stopped, two conditions must be met
        #          1. course has NO current lesson
        #          2. course desktops count equal 0
        # "switching": the course not in started or stopped status,
        #              namely course changing from start to stop or wise verse.
        #              some conditions must be met
        #          1. course has current lesson, but desktop count not met capacity or
        #             met capacity but not all in active or using status
        #          2. course has NO current lesson, but desktop count NOT equal to 0
        ######################################
        if desktop_count == 0:
            if current_lesson:
                result['status'] = 'switching'
            else:
                result['status'] = 'stop'
        elif desktop_count != course.capacity:
            result['status'] = 'switching'
        else:
            desktops = Desktop.query.filter_by(course_id=id, desktop_type=DesktopType.COURSE)
            result['status'] = 'start'
            for desktop in desktops:
                if desktop.vm_state != 'ACTIVE' and desktop.vm_state != 'USING':
                    result['status'] = 'switching'
                    break
            if not current_lesson:
                result['status'] = 'switching'
    else:
        result['status'] = 'error'
    db.session.remove()
    return jsonify(result)



