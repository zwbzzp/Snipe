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
from ..audit import ResourceController
from . import edu
from .forms import CourseForm, UploadStudentFileForm, CustomizedLessonForm, StudentListForm, \
    TempLessonForm, LessonForm, default_of_protocol, choice_of_place, choice_of_protocol,\
    choices_of_flavors, choices_of_networks, choices_of_images, default_of_policy, choice_of_policy
from .utils import get_date_from_weekday, next_day, next_week, \
    get_this_week_start_and_end_date, get_timetable_of_this_week, get_timetable_of_given_week, \
    redefine_all_lessons

from ..models import Period, Course, Role, User, Lesson, Place, Desktop, DesktopType, Protocol, \
    DesktopType, FtpAccount, Image, Flavor, Policy
from .. import db, csrf
from phoenix.cloud import image as OpenstackImageService
from phoenix.cloud import network as OpenstackNetworkService
from phoenix.cloud import compute as OpenstackComputeService

from ..common import imageutils

LOG = logging.getLogger(__name__)
ua_logger = UserActionLogger()


@edu.route('/timetable', methods=['GET'])
@login_required
def timetable():
    periods = Period.query.all()
    return render_template('edu/timetable.html', period_list=periods)


@edu.route('/courses', methods=['GET'])
@login_required
def courses():
    create_course_form = CourseForm()
    temp_lesson_form = TempLessonForm()
    if current_user.is_administrator():
        # administrator, all course
        courses = Course.query.all()
        for c in courses:
            # any lesson is running?
            now = datetime.datetime.now()
            c.lesson_now = c.find_current_lesson(now)
        return render_template('edu/courses.html', courses=courses,
                               create_course_form=create_course_form, temp_lesson_form=temp_lesson_form)
    elif current_user.role.name == 'Teacher':
        # teacher, as a owner
        courses = Course.query.filter_by(owner_id=current_user.id).all()
        for c in courses:
            # any lesson is running?
            now = datetime.datetime.now()
            c.lesson_now = c.find_current_lesson(now)
        return render_template('teachers/edu/courses.html', courses=courses,
                               create_course_form=create_course_form, temp_lesson_form=temp_lesson_form)
    else:
        # other students
        courses = current_user.courses
        for c in courses:
            # any lesson is running?
            now = datetime.datetime.now()
            c.lesson_now = c.find_current_lesson(now)
        return render_template('students/edu/courses.html', courses=courses)


@edu.route('/courses/', methods=['GET', 'POST'])
@login_required
def create_course():
    session["course_op"] = "create"

    # FIXME: init of WTForm protocol default value. Cause can not init in the form by protocol default value.
    form = CourseForm(protocol=default_of_protocol(), policy_id=default_of_policy())

    if form.validate_on_submit():
        protocol = Protocol.query.\
            filter(Protocol.id == form.protocol.data).first()
        policy = Policy.query. \
            filter(Policy.id == form.policy_id.data).first()
        course = Course(name = form.name.data,
                        start_date = form.start_date.data,
                        end_date = form.end_date.data,
                        capacity = form.capacity.data,
                        image_ref = form.image_ref.data,
                        flavor_ref = form.flavor_ref.data,
                        network_ref = form.network_ref.data,
                        owner_id = form.owner_id.data,
                        protocol = protocol.name if protocol else None,
                        policy_id = policy.id if policy else None)
        for place_id in form.places.data:
            course.places.append(Place.query.get(place_id))

        db.session.add(course)
        db.session.flush()

        # for non-login mode
        places = course.places
        for place in places:
            terminals = place.terminals
            for terminal in terminals:
                user = terminal.user
                if user:
                    course.users.append(user)
        db.session.commit()

        ua_logger.info(current_user, "创建课程: %s_%s" % (course.id, course.name))
        LOG.info("Add course %s" % course)
        flash(
            '课程《{0}》创建成功'.format(form.name.data),
            'info'
        )
        return redirect(url_for('edu.create_lesson', id=course.id))

    image_list = imageutils.list_of_image()
    return render_template('edu/course_create.html', form=form, image_list=image_list)


# @edu.route('/course/<int:id>', methods=['GET'])
# @login_required
# def course_detail(id):
#     session["course_op"] = "edit"
#     course = Course.query.filter_by(id=id).first()
#     if not course:
#         abort(404)
#     protocol = Protocol.query.filter(Protocol.name == course.protocol).first()
#     form = CourseForm(name=course.name, owner_id=course.owner_id,
#                       start_date=course.start_date,
#                       end_date=course.end_date, capacity=course.capacity,
#                       image_ref=course.image_ref, flavor_ref=course.flavor_ref,
#                       network_ref=course.network_ref,
#                       places=[places.id for places in course.places.all()],
#                       protocol = protocol.id if protocol else None)
#
#     timetable_of_this_week = get_timetable_of_this_week(course)
#     image_list = imageutils.list_of_image()
#     return render_template('edu/course_detail.html', form=form,
#                            week_date=get_this_week_start_and_end_date(),
#                            course=course,
#                            timetable=timetable_of_this_week,
#                            image_list=image_list)

@edu.route('/course/<int:id>', methods=['GET'])
@login_required
def course_detail(id):
    session["course_op"] = "edit"
    course = Course.query.filter_by(id=id).first()
    if not course:
        abort(404)
    protocol = Protocol.query.filter(Protocol.name == course.protocol).first()
    policy = Policy.query.filter(Policy.id == course.policy_id).first()
    form = CourseForm(name=course.name, owner_id=course.owner_id,
                      start_date=course.start_date,
                      end_date=course.end_date, capacity=course.capacity,
                      image_ref=course.image_ref, flavor_ref=course.flavor_ref,
                      network_ref=course.network_ref,
                      places=[places.id for places in course.places.all()],
                      protocol = protocol.id if protocol else None,
                      policy_id=policy.id if policy else None)
    upload_student_form = UploadStudentFileForm()
    student_list_form = StudentListForm()
    timetable_of_this_week = get_timetable_of_this_week(course)
    course_owner = User.query.filter_by(id=course.owner_id).first()
    course_image = Image.query.filter_by(ref_id=course.image_ref).first()
    course_flavor = Flavor.query.filter_by(ref_id=course.flavor_ref).first()
    course_policy = Policy.query.filter_by(id=course.policy_id).first()
    course_flavor_list = OpenstackComputeService.list_flavors()
    for flavor in course_flavor_list:
         if flavor.id == course.flavor_ref:
              course_flavor_description = "%s - %sVCPU|%sMB|%sGB" % (flavor.name, flavor.vcpus, flavor.ram, flavor.disk)
    course_network_list = OpenstackNetworkService.list_networks()
    for net in course_network_list.get("networks"):
        if net["id"] == course.network_ref:
            course_network = net["name"]
    places_list = choice_of_place()
    protocol_list = choice_of_protocol()
    policy_list = choice_of_policy()
    flavors_list = choices_of_flavors()
    image_list = choices_of_images()
    network_list = choices_of_networks()
    role = current_user.role
    lesson_form = LessonForm()
    image_detail_list = imageutils.list_of_image()
    return render_template('edu/course_detail.html',role=role.name,form=form,upload_student_form=upload_student_form,student_list_form=student_list_form,lesson_form=lesson_form,
                           week_date=get_this_week_start_and_end_date(),policy_list=policy_list,course_policy=course_policy,
                           course=course,course_owner=course_owner,course_image=course_image,course_flavor=course_flavor,
                           course_flavor_description=course_flavor_description,image_detail_list=image_detail_list,
                           course_network=course_network,timetable=timetable_of_this_week,
                           places_list=places_list,protocol_list=protocol_list,flavors_list=flavors_list,image_list=image_list,network_list=network_list)

@edu.route('/course/<int:id>/week_date', methods=['POST'])
@login_required
def get_timetable(id):
    start_date_str = request.values.get("week_start_date", "")
    course = Course.query.filter_by(id=id).first()
    # result = {'result': 'success',
    #           'parameters': None}
    date = datetime.datetime.strptime(start_date_str, '%Y-%m-%d').date()
    start_date = timeutils.get_week_start_date(date)
    end_date = timeutils.get_week_end_date(date)
    week_date = (start_date, end_date)
    timetable = get_timetable_of_given_week(course, start_date_str)
    return render_template('edu/week_timetable.html', week_date=week_date, timetable=timetable)

@edu.route('/course/<int:id>', methods=['POST'])
@login_required
def update_course(id):
    course = Course.query.filter_by(id=id).first()
    if course is None:
        abort(404)
    form = CourseForm()
    upload_student_form = UploadStudentFileForm()
    student_list_form = StudentListForm()
    lesson_form = LessonForm()
    success_count = 0
    fail_count = 0
    result={"result":"success"}

    if form.validate_on_submit():
        course.name = form.name.data
        course.start_date = form.start_date.data
        course.end_date = form.end_date.data

        # audit capacity
        course.capacity = form.capacity.data
        course.flavor_ref = form.flavor_ref.data
        resource_controller = ResourceController()
        for lesson in course.lessons:
            if not resource_controller.audit_schedule_lesson(lesson):
                db.session.rollback()
                flash("资源使用超出系统上限", 'error')
                LOG.debug('Could not update course, resource exceed system limit')
                return redirect(url_for('edu.course_detail', id=id))

        course.image_ref = form.image_ref.data
        course.network_ref = form.network_ref.data
        protocol = Protocol.query.\
            filter(Protocol.id == form.protocol.data).first()
        course.protocol = protocol.name if protocol else None

        owner_id = form.owner_id.data
        owner = User.query.filter_by(id=owner_id).first()
        if owner is not None:
            course.owner = owner

        policy = Policy.query. \
            filter(Policy.id == form.policy_id.data).first()
        if policy is not None:
            course.policy = policy


        # remove all places alone with terminal users in that place
        for place in course.places:
            course.places.remove(place)
            terminals = place.terminals
            for terminal in terminals:
                course.users.remove(terminal.user)

        for place_id in form.places.data:
            place = Place.query.get(place_id)
            course.places.append(place)

        # for non-login mode
        places = course.places
        for place in places:
            terminals = place.terminals
            for terminal in terminals:
                user = terminal.user
                if user:
                    course.users.append(user)

        db.session.add(course)
        db.session.commit()
        flash("修改基本信息成功", 'info')
        ua_logger.info(current_user, "修改课程: %s_%s" % (course.id, course.name))
        LOG.info("Update course %s" % course)
        return redirect(url_for("edu.course_detail", id=id))
    elif upload_student_form.validate_on_submit():
        try:
            data = xlrd.open_workbook(file_contents=upload_student_form.file.data.read())
        except:
            flash('请上传正确的表格', "error")
            return redirect(url_for("edu.course_detail", id=id))
        try:
            table = data.sheet_by_index(0)
            students = map(lambda d: d.value, table.col(0)[1:])
        except:
            flash('请上传正确的表格', "error")
            return redirect(url_for("edu.course_detail", id=id))
        for student_username in students:
            student = User.query.outerjoin(User.role).filter(and_(Role.name == 'Student',
                                                                  User.username == student_username)).first()
            try:
                if student:
                    course.users.append(student)
                    db.session.commit()
                    success_count += 1
                    LOG.info("Insert student %s into course %s" % (student, course))
                    flash(
                        '学生{0}添加成功'.format(student.username),
                        'info'
                    )
                else:
                    fail_count += 1
                    LOG.error("Unable to insert student %s into course %s, student does not exist" % (
                    student_username, course))
                    flash(
                        '学生{0}不存在，添加失败'.format(student_username),
                        'error'
                    )
            except IntegrityError:
                db.session.rollback()
                fail_count += 1
                LOG.error(
                    "Unable to insert student %s into course %s, student has existed" % (student_username, course))
                flash(
                    '学生{0}已经存在于名单中，添加失败'.format(student.username),
                    'error'
                )
        flash(
            '尝试添加{0}个学生,其中成功{1}个,失败{2}个'.format(
                success_count + fail_count,
                success_count,
                fail_count),
            'info'
        )
        ua_logger.info(current_user, "导入学生成功%s个,失败%s个" % (success_count, fail_count))
        return redirect(url_for("edu.course_detail", id=id))
    elif student_list_form.validate_on_submit():
        students_id = [int(data.strip()) for data in student_list_form.students.data.split(",")]
        for student_id in students_id:
            student = User.query.get(student_id)
            try:
                if student:
                    course.users.append(student)
                    db.session.commit()
                    success_count += 1
                    LOG.info("Insert student %s into course %s" % (student, course))
                    flash(
                        '学生{0}添加成功'.format(student.username),
                        'info'
                    )
            except IntegrityError:
                db.session.rollback()
                fail_count += 1
                LOG.error("Unable to insert student %s into course %s, student has existed" % (student, course))
                flash(
                    '学生{0}已经存在于名单中，添加失败'.format(student.username),
                    'error'
                )
        flash(
            '尝试添加{0}个学生,其中成功{1}个,失败{2}个'.format(
                success_count + fail_count,
                success_count,
                fail_count),
            'info'
        )
        ua_logger.info(current_user, "添加学生成功%s个,失败%s个" % (success_count, fail_count))
        return redirect(url_for("edu.course_detail", id=id))
    # return render_template('edu/student_create.html',
    #                        operation=session.get("course_op"),
    #                        upload_student_form=upload_student_form,
    #                        student_list_form=student_list_form,
    #                        course=course)

    elif lesson_form.validate_on_submit():
        start_time_type = lesson_form.start_time_type.data
        if start_time_type == "period":
            start_period_id = lesson_form.start_period_id.data
            start_period = Period.query.get_or_404(start_period_id)
            start_time = start_period
        else:
            start_time = lesson_form.start_time.data.time()

        end_time_type = lesson_form.end_time_type.data
        if end_time_type == "period":
            end_period_id = lesson_form.end_period_id.data
            end_period = Period.query.get_or_404(end_period_id)
            end_time = end_period
        else:
            end_time = lesson_form.end_time.data.time()

        start_date = lesson_form.start_date.data
        end_date = lesson_form.end_date.data
        start_weekday = lesson_form.start_weekday.data
        end_weekday = lesson_form.end_weekday.data

        frequency = lesson_form.frequency.data
        lessons = []
        if frequency == 'once':
            lesson = Lesson(course_id=course.id, start_date=start_date,
                            end_date=end_date)
            lesson.start_time = start_time
            lesson.end_time = end_time
            lessons.append(lesson)
        elif frequency == 'weekly':
            start_date = timeutils.now().date()
            if start_date < course.start_date:
                start_date = course.start_date
            delta_days = start_weekday - start_date.weekday()
            if delta_days < 0:
                delta_days += 7
            start_date += datetime.timedelta(days=delta_days)
            end_date = start_date + datetime.timedelta(days=(end_weekday - start_weekday))
            while end_date <= course.end_date:
                lesson = Lesson(course_id=course.id, start_date=start_date,
                                end_date=end_date)
                lesson.start_time = start_time
                lesson.end_time = end_time
                lessons.append(lesson)
                start_date += datetime.timedelta(days=7)
                end_date += datetime.timedelta(days=7)
        elif frequency == 'daily':
            start_date = timeutils.now().date()
            if start_date < course.start_date:
                start_date = course.start_date
            end_date = start_date
            while end_date <= course.end_date:
                lesson = Lesson(course_id=course.id, start_date=start_date,
                                end_date=end_date)
                lesson.start_time = start_time
                lesson.end_time = end_time
                lessons.append(lesson)
                start_date += datetime.timedelta(days=1)
                end_date = start_date

        # Check time conflicts
        fails = []
        success = []
        for lesson in lessons:
            if course.find_conflict_lessons(lesson.start_datetime, lesson.end_datetime):
                fails.append(lesson)
                flash('时间段冲突 %s ~ %s' % ((lesson.start_datetime).strftime('%Y-%m-%d %H:%M'),
                                     (lesson.end_datetime).strftime('%Y-%m-%d %H:%M')),
                      category='error')
            else:
                success.append(lesson)
        # Resource audit
        resource_controller = ResourceController()
        for lesson in success:
            if not resource_controller.audit_schedule_lesson(lesson):
                fails.append(lesson)
                flash('时间段超出系统资源上限 %s ~ %s' % ((lesson.start_datetime).strftime('%Y-%m-%d %H:%M'),
                                         (lesson.end_datetime).strftime('%Y-%m-%d %H:%M')),
                      category='error')
            else:
                db.session.add(lesson)
                LOG.info('Create lesson %r of course %r' % (lesson, course))
                flash('添加时间段 %s ~ %s' % ((lesson.start_datetime).strftime('%Y-%m-%d %H:%M'),
                                         (lesson.end_datetime).strftime('%Y-%m-%d %H:%M')), category='info')
        db.session.commit()

        flash('尝试添加{0}个时间段,其中成功{1}个,失败{2}个'.format(len(lessons), len(lessons) - len(fails), len(fails)),
              category='info')
        ua_logger.info(current_user, "添加课时成功%s个,失败%s个" % (len(lessons) - len(fails), len(fails)))
        lessons = course.lessons.order_by(db.asc(Lesson.start_date), db.asc(Lesson._start_time))
        timetable_of_this_week = get_timetable_of_this_week(course)
        redefine_all_lessons(course)
        # return render_template('edu/setting_timetable.html',
        #                    week_date=get_this_week_start_and_end_date(),
        #                    timetable=timetable_of_this_week,
        #                    course=course,
        #                    lessons=lessons,
        #                    lesson_form=lesson_form)
        return redirect(url_for("edu.course_detail", id=id))

    return redirect(url_for("edu.course_detail", id=id))

@edu.route('/course/<int:id>/save_timetable', methods=['POST'])
@login_required
def save_timetable(id):
    course = Course.query.filter_by(id=id).first()
    if course is None:
        abort(404)
    change_timetables = request.json
    result = {
        "result" : "success",
        "message" : {}
    }
    message = {
        "success" : [],
        "fail" : []
    }
    add_lessons = []
    for timetable in change_timetables["add_lessons_lists"]:
        for item in change_timetables["add_lessons_lists"][timetable]:
            start_date = datetime.datetime.strptime(timetable, '%Y-%m-%d').date() + datetime.timedelta(
                int(item.split("_")[1]))
            start_time = Period.query.filter_by(name=item.split("_")[0]).first().start_time
            end_date = datetime.datetime.strptime(timetable, '%Y-%m-%d').date() + datetime.timedelta(int(item.split("_")[1]))
            end_time = Period.query.filter_by(name=item.split("_")[0]).first().end_time
            lesson = Lesson(course_id=course.id, start_date=start_date, end_date=end_date)
            lesson.start_time = start_time
            lesson.end_time = end_time
            lesson.start_period =  Period.query.filter_by(name=item.split("_")[0]).first()
            lesson.end_period = Period.query.filter_by(name=item.split("_")[0]).first()
            add_lessons.append(lesson)
    fails = []
    success = []
    for lesson in add_lessons:
        if course.find_conflict_lessons(lesson.start_datetime, lesson.end_datetime):
            fails.append(lesson)
            flash('时间段冲突 %s ~ %s' % ((lesson.start_datetime).strftime('%Y-%m-%d %H:%M'),
                                     (lesson.end_datetime).strftime('%Y-%m-%d %H:%M')),
                  category='error')
            message["fail"].append('时间段冲突 %s ~ %s' % ((lesson.start_datetime).strftime('%Y-%m-%d %H:%M'),
                                     (lesson.end_datetime).strftime('%Y-%m-%d %H:%M')))
        else:
            if lesson.start_date < course.start_date or lesson.end_date > course.end_date:
                flash('时间段超出课程时间限制 %s ~ %s' % ((lesson.start_datetime).strftime('%Y-%m-%d %H:%M'),
                                               (lesson.end_datetime).strftime('%Y-%m-%d %H:%M')), category='error')
                message["fail"].append('时间段超出课程时间限制 %s ~ %s' % ((lesson.start_datetime).strftime('%Y-%m-%d %H:%M'),
                                                                (lesson.end_datetime).strftime('%Y-%m-%d %H:%M')))
                fails.append(lesson)
            else:
                success.append(lesson)
            # Resource audit
    resource_controller = ResourceController()
    for lesson in success:
        if not resource_controller.audit_schedule_lesson(lesson):
            fails.append(lesson)
            flash('时间段超出系统资源上限 %s ~ %s' % ((lesson.start_datetime).strftime('%Y-%m-%d %H:%M'),
                                         (lesson.end_datetime).strftime('%Y-%m-%d %H:%M')),category='error')
            message["fail"].append('时间段超出系统资源上限 %s ~ %s' % ((lesson.start_datetime).strftime('%Y-%m-%d %H:%M'),
                                         (lesson.end_datetime).strftime('%Y-%m-%d %H:%M')))
        else:
            db.session.add(lesson)
            LOG.info('Create lesson %r of course %r' % (lesson, course))
            flash('添加时间段 %s ~ %s' % ((lesson.start_datetime).strftime('%Y-%m-%d %H:%M'),
                                     (lesson.end_datetime).strftime('%Y-%m-%d %H:%M')),category='info')
            message["success"].append('添加时间段 %s ~ %s' % ((lesson.start_datetime).strftime('%Y-%m-%d %H:%M'),
                                     (lesson.end_datetime).strftime('%Y-%m-%d %H:%M')))
    db.session.commit()
    if len(add_lessons) != 0:
        flash('尝试添加{0}个时间段,其中成功{1}个,失败{2}个'.format(len(add_lessons), len(add_lessons) - len(fails), len(fails)),
              category='info')
        message["success"].append('尝试添加{0}个时间段,其中成功{1}个,失败{2}个'.format(len(add_lessons), len(add_lessons) - len(fails), len(fails)))
        ua_logger.info(current_user, "添加课时成功%s个,失败%s个" % (len(add_lessons) - len(fails), len(fails)))

    for timetable in change_timetables["delete_lessons_lists"]:
        for item in change_timetables["delete_lessons_lists"][timetable]:
            start_date = datetime.datetime.strptime(timetable, '%Y-%m-%d').date() + datetime.timedelta(
                int(item.split("_")[1]))

            end_date = datetime.datetime.strptime(timetable, '%Y-%m-%d').date() + datetime.timedelta(
                int(item.split("_")[1]))

            period_id = item.split("_")[0]
            max_period = 1
            for period in Period.query.all():
                if int(period.name) > max_period:
                    max_period = int(period.name)
            if period_id == '1':
                pre_period_id = str(max_period)
                pre_start_date = start_date - datetime.timedelta(days=1)
            else:
                pre_period_id = str(int(period_id) - 1)
                pre_start_date = start_date
            if period_id == str(max_period):
                next_period_id = '1'
                next_start_date = start_date + datetime.timedelta(days=1)

            else:
                next_period_id = str(int(period_id) + 1)
                next_start_date = start_date

            start_datetime = datetime.datetime.combine(pre_start_date, Period.query.filter_by( name=pre_period_id).first().end_time)
            end_datetime = datetime.datetime.combine(next_start_date,Period.query.filter_by(name=next_period_id).first().start_time)

            lessons = Lesson.query.filter_by(course_id=course.id).all()
            for lesson in lessons:
                lesson_start_datetime = datetime.datetime.combine(lesson.start_date, lesson.start_time)
                lesson_end_datetime = datetime.datetime.combine(lesson.end_date, lesson.end_time)
                if lesson_start_datetime < start_datetime and lesson_end_datetime > end_datetime:
                    lesson1 = Lesson(course_id=course.id, start_date=lesson.start_date, end_date=pre_start_date,
                                     start_time=lesson.start_time,
                                     end_time=Period.query.filter_by(name=pre_period_id).first().end_time)
                    lesson1.start_period = lesson.start_period
                    lesson1.end_period = Period.query.filter_by(name=pre_period_id).first()
                    lesson2 = Lesson(course_id=course.id, start_date=next_start_date, end_date=lesson.end_date,
                                     start_time=Period.query.filter_by(name=next_period_id).first().start_time,
                                     end_time=lesson.end_time)
                    lesson2.start_period = Period.query.filter_by(name=next_period_id).first()
                    lesson2.end_period = lesson.end_period
                    course.lessons.remove(lesson)
                    db.session.add(lesson1)
                    db.session.add(lesson2)
                elif lesson_start_datetime >= start_datetime and end_datetime >= lesson_start_datetime and end_datetime < lesson_end_datetime:
                    lesson.start_time = Period.query.filter_by(name=next_period_id).first().start_time
                    lesson.start_date = next_start_date
                    lesson.start_period = Period.query.filter_by(name=next_period_id).first()
                    lesson.start_period_id = int(next_period_id)
                    db.session.add(lesson)
                elif lesson_start_datetime < start_datetime and start_datetime <= lesson_end_datetime and end_datetime >= lesson_end_datetime:
                    lesson.end_time = Period.query.filter_by(name=pre_period_id).first().end_time
                    lesson.end_date = pre_start_date
                    lesson.end_period = Period.query.filter_by(name=pre_period_id).first()
                    lesson.end_period_id = int(pre_period_id)
                    db.session.add(lesson)
                elif lesson_start_datetime >= start_datetime and lesson_end_datetime <= end_datetime:
                    course.lessons.remove(lesson)
                else:
                    pass
            flash('上课时段 {0} ~ {1} 删除成功'.format((datetime.datetime.combine(start_date, Period.query.filter_by( name=period_id).first().start_time)).strftime('%Y-%m-%d %H:%M'),
                                             (datetime.datetime.combine(end_date, Period.query.filter_by(name=period_id).first().end_time)).strftime('%Y-%m-%d %H:%M')),'info')
            message["fail"].append('上课时段 {0} ~ {1} 删除成功'.format((start_datetime).strftime('%Y-%m-%d %H:%M'),
                            (end_datetime).strftime('%Y-%m-%d %H:%M')))
        db.session.add(course)
        db.session.commit()
    redefine_all_lessons(course)
    return jsonify(message)

@edu.route('/course/<int:id>/delay', methods=['POST'])
@login_required
def delay_course(id):
    course = Course.query.filter_by(id=id).first()
    latency = request.json
    if course:
        lesson = course.find_current_lesson()
        if lesson is None:
            return jsonify({
                'status': 'fail',
                'data': 'not running',
            })

        extra_lesson_end_time = (datetime.datetime.combine(lesson.end_date, lesson._end_time) +
                                 datetime.timedelta(seconds=latency))\
            .time()
        extra_lesson = Lesson(course_id=course.id,
                              start_date=lesson.start_date,
                              end_date=lesson.end_date,
                              _start_time=lesson.end_time,
                              _end_time=extra_lesson_end_time)
        if not ResourceController().audit_schedule_lesson(extra_lesson):
            return jsonify({'status': 'fail',
                            'data': 'resource exceed system limit'})
        try:
            desktop_count = course.delay(latency)
        except:
            LOG.exception('Unable to delay course %s' % course)
            return jsonify({
                'status': 'fail',
                'data': None
            })
        LOG.info("%s(%s) delay course %s",
                  current_user.username, current_user.role.name, course)
        ua_logger.info(current_user, "延长课程 %s 上课时间至 %s" % (id, lesson.end_datetime))
        return jsonify({'status': 'success',
                        'data': None})
    else:
        return jsonify({'status': 'fail',
                        'data': 'course not exist'})


@edu.route('/course/<int:id>', methods=['DELETE'])
@login_required
def delete_course(id):
    course = Course.query.get(id=id)
    if course is None:
        LOG.warn("Delete an non-exists course %s" % course)
        abort(404)
    else:
        desktop_count = course.desktops.count()
        current_lesson = course.find_current_lesson()

        # TODO when course still has desktops, what should be done?
        if desktop_count > 0:
            LOG.error("Unable to delete course %s, still have %s desktops" % (course.id, desktop_count))
        elif current_lesson is not None:
            LOG.error('Unable to delete course %s, lesson %s is running' % (course, current_lesson))
        else:
            FtpAccount.query.filter_by(course_id=course.id).delete()
            db.session.delete(course)
            ua_logger.info("删除课程: %s_%s" % (course.id, course.name))
            LOG.info("Delete course %s" % course)
    db.session.commit()
    return {"result": "success"}


@edu.route('/courses/', methods=['DELETE'])
@login_required
def delete_courses():
    courses = request.json
    result_json = {
        'result': 'success',
        'success_list': [],
        'fail_list': [],
    }
    for course_id in courses:
        course = Course.query.filter_by(id=course_id).first()
        if course is None:
            result_json['fail_list'].append({"id":course.id, "name":course.name})
            LOG.warn("Delete an non-exists course %s" % course)
        else:
            desktop_count = course.desktops.count()
            current_lesson = course.find_current_lesson()
            # TODO when course still has desktops, what should be done?
            if desktop_count > 0:
                result_json['fail_list'].append({"id":course.id, "name":course.name})
                LOG.error("Unable to delete course %s, still have %s desktops" % (course.id, desktop_count))
            elif current_lesson is not None:
                LOG.error('Unable to delete course %s, lesson %s is running' % (course, current_lesson))
                result_json['fail_list'].append({'id':course.id, 'name':course.name})
            else:
                result_json['success_list'].append({"id":course.id, "name":course.name})
                Lesson.query.filter_by(course_id=course.id).delete()
                FtpAccount.query.filter_by(course_id=course.id).delete()
                db.session.delete(course)
                ua_logger.info(current_user, "批量删除课程: %s_%s" % (course.id, course.name))
                LOG.info("Delete course %s" % course)
    db.session.commit()
    return jsonify(result_json)


@edu.route('/course/<int:id>/lessons', methods=['GET', 'POST'])
@login_required
def create_lesson(id):
    course = Course.query.filter_by(id=id).first()
    if not course:
        abort(404)

    lesson_form = LessonForm()
    if lesson_form.validate_on_submit():
        start_time_type = lesson_form.start_time_type.data
        if start_time_type == "period":
            start_period_id = lesson_form.start_period_id.data
            start_period = Period.query.get_or_404(start_period_id)
            start_time = start_period
        else:
            start_time = lesson_form.start_time.data.time()

        end_time_type = lesson_form.end_time_type.data
        if end_time_type == "period":
            end_period_id = lesson_form.end_period_id.data
            end_period = Period.query.get_or_404(end_period_id)
            end_time = end_period
        else:
            end_time = lesson_form.end_time.data.time()

        start_date = lesson_form.start_date.data
        end_date = lesson_form.end_date.data
        start_weekday = lesson_form.start_weekday.data
        end_weekday = lesson_form.end_weekday.data

        frequency = lesson_form.frequency.data
        lessons = []
        if frequency == 'once':
            lesson = Lesson(course_id=course.id, start_date=start_date,
                            end_date=end_date)
            lesson.start_time = start_time
            lesson.end_time = end_time
            lessons.append(lesson)
        elif frequency == 'weekly':
            start_date = timeutils.now().date()
            if start_date < course.start_date:
                start_date = course.start_date
            delta_days = start_weekday - start_date.weekday()
            if delta_days < 0:
                delta_days += 7
            start_date += datetime.timedelta(days=delta_days)
            end_date = start_date + datetime.timedelta(days=(end_weekday - start_weekday))
            while end_date <= course.end_date:
                lesson = Lesson(course_id=course.id, start_date=start_date,
                            end_date=end_date)
                lesson.start_time = start_time
                lesson.end_time = end_time
                lessons.append(lesson)
                start_date += datetime.timedelta(days=7)
                end_date += datetime.timedelta(days=7)
        elif frequency == 'daily':
            start_date = timeutils.now().date()
            if start_date < course.start_date:
                start_date = course.start_date
            end_date = start_date
            while end_date <= course.end_date:
                lesson = Lesson(course_id=course.id, start_date=start_date,
                            end_date=end_date)
                lesson.start_time = start_time
                lesson.end_time = end_time
                lessons.append(lesson)
                start_date += datetime.timedelta(days=1)
                end_date = start_date

        # Check time conflicts
        fails = []
        success = []
        for lesson in lessons:
            if course.find_conflict_lessons(lesson.start_datetime, lesson.end_datetime):
                fails.append(lesson)
                flash('时间段冲突 %s ~ %s' % (timeutils.format_datetime(lesson.start_datetime),
                                            timeutils.format_datetime(lesson.end_datetime)),
                      category='error')
            else:
                success.append(lesson)
        # Resource audit
        resource_controller = ResourceController()
        for lesson in success:
            if not resource_controller.audit_schedule_lesson(lesson):
                fails.append(lesson)
                flash('时间段超出系统资源上限 %s ~ %s' % (timeutils.format_datetime(lesson.start_datetime),
                                            timeutils.format_datetime(lesson.end_datetime)),
                      category='error')
            else:
                db.session.add(lesson)
                LOG.info('Create lesson %r of course %r' % (lesson, course))
        db.session.commit()

        flash('尝试添加{0}个时间段,其中成功{1}个,失败{2}个'.format(len(lessons), len(lessons)-len(fails), len(fails)),
              category='info')
        ua_logger.info(current_user, "添加课时成功%s个,失败%s个" % (len(lessons)-len(fails), len(fails)))
        return redirect(url_for('edu.create_lesson', id=id))

    # when the form submited is invalid, errors will be non-null
    if lesson_form.errors:
        flash(
            '上课时段添加失败，{0}'.format(lesson_form.errors),
            'error'
        )
        LOG.error("Create lesson fail, %s" % lesson_form.errors)

    lessons = course.lessons.order_by(db.asc(Lesson.start_date), db.asc(Lesson._start_time))
    timetable_of_this_week = get_timetable_of_this_week(course)
    return render_template('edu/lesson_create.html',
                           week_date=get_this_week_start_and_end_date(),
                           operation=session.get("course_op"),
                           timetable=timetable_of_this_week,
                           course=course,
                           lessons=lessons,
                           lesson_form=lesson_form)

@edu.route('/course/<int:id>/students', methods=['GET', 'POST'])
@login_required
def upload_students(id):
    course = Course.query.filter_by(id=id).first()
    if not course:
        abort(404)
    upload_student_form = UploadStudentFileForm()
    student_list_form = StudentListForm()
    success_count = 0
    fail_count = 0
    if upload_student_form.validate_on_submit():
        try:
            data = xlrd.open_workbook(file_contents=upload_student_form.file.data.read())
        except:
            flash('请上传正确的表格', "error")
            return redirect(url_for("edu.upload_students", id=id))
        try:
            table = data.sheet_by_index(0)
            students = map(lambda d: d.value, table.col(0)[1:])
        except:
            flash('请上传正确的表格', "error")
            return redirect(url_for("edu.upload_students", id=id))
        for student_username in students:
            student = User.query.outerjoin(User.role).filter(and_(Role.name == 'Student',
                                        User.username == student_username)).first()
            try:
                if student:
                    course.users.append(student)
                    db.session.commit()
                    success_count += 1
                    LOG.info("Insert student %s into course %s" % (student, course))
                    flash(
                        '学生{0}添加成功'.format(student.username),
                        'info'
                    )
                else:
                    fail_count += 1
                    LOG.error("Unable to insert student %s into course %s, student does not exist" % (student_username, course))
                    flash(
                        '学生{0}不存在，添加失败'.format(student_username),
                        'error'
                    )
            except IntegrityError:
                db.session.rollback()
                fail_count += 1
                LOG.error("Unable to insert student %s into course %s, student has existed" % (student_username, course))
                flash(
                    '学生{0}已经存在于名单中，添加失败'.format(student.username),
                    'error'
                )
        flash(
            '尝试添加{0}个学生,其中成功{1}个,失败{2}个'.format(
                success_count + fail_count,
                success_count,
                fail_count),
            'info'
        )
        ua_logger.info(current_user, "导入学生成功%s个,失败%s个" % (success_count, fail_count))
        return redirect(url_for("edu.upload_students", id=id))
    elif student_list_form.validate_on_submit():
        students_id = [int(data.strip()) for data in student_list_form.students.data.split(",")]
        for student_id in students_id:
            student = User.query.get(student_id)
            try:
                if student:
                    course.users.append(student)
                    db.session.commit()
                    success_count += 1
                    LOG.info("Insert student %s into course %s" % (student, course))
                    flash(
                        '学生{0}添加成功'.format(student.username),
                        'info'
                    )
            except IntegrityError:
                db.session.rollback()
                fail_count += 1
                LOG.error("Unable to insert student %s into course %s, student has existed" % (student, course))
                flash(
                    '学生{0}已经存在于名单中，添加失败'.format(student.username),
                    'error'
                )
        flash(
            '尝试添加{0}个学生,其中成功{1}个,失败{2}个'.format(
                success_count + fail_count,
                success_count,
                fail_count),
            'info'
        )
        ua_logger.info(current_user, "添加学生成功%s个,失败%s个" % (success_count, fail_count))
        return redirect(url_for("edu.upload_students", id=id))
    return render_template('edu/student_create.html',
                           operation=session.get("course_op"),
                           upload_student_form=upload_student_form,
                           student_list_form=student_list_form,
                           course=course)


@edu.route('/courses/<int:id>/students', methods=['DELETE'])
@login_required
def delete_students(id):
    course = Course.query.filter_by(id=id).first()
    # success_list = []
    # fail_list = []
    if course is not None:
        students = request.json
        for student_id in students:
            student = User.query.filter_by(id=student_id).first()
            if student is not None:
                course.users.remove(student)
                # success_list.append(student_id)
                LOG.info("Remove user %s from course %s" % (student_id, id))
                try:
                    db.session.flush()
                    LOG.info("Delete student %s from course %s" % (student, course))
                    flash(
                        '学生%s删除成功' % student.username,
                        'info'
                    )
                    ua_logger.info(current_user, "从课程 %s 中删除学生 %s" % (course.id, student.id))
                except:
                    db.session.rollback()
                    # flash(student.username, "not_exist")
            else:
                # fail_list.append(student_id)
                LOG.warn("Try to remove user %s from course %s, but user is not registered" %(student_id, course))
        db.session.add(course)
        db.session.commit()
    result_json = {
        "result": "success",
        # "success_list": success_list,
        # "fail_list": fail_list,
    }
    return jsonify(result_json)


@edu.route('/course/<int:id>/lessons', methods=['DELETE'])
@login_required
def delete_lessons(id):
    course = Course.query.filter_by(id=id).first()
    if course is not None:
        lessons = request.json
        for lesson_id in lessons:
            lesson = Lesson.query.filter_by(id=lesson_id).first()
            if lesson is not None:
                course.lessons.remove(lesson)
                flash(
                    '上课时段{0} ~ {1}删除成功'.format(
                        timeutils.format_datetime(lesson.start_datetime),
                        timeutils.format_datetime(lesson.end_datetime)),
                    'info'
                )
                LOG.info("Delete lesson %s from course %s" % (lesson, course))
        db.session.add(course)
        db.session.commit()
        ua_logger.info(current_user, "删除课时: %s-%s" % (lesson.start_datetime, lesson.end_datetime))
    result_json = {
        "result": "success",
    }
    return jsonify(result_json)


# ajax Router
@edu.route('/teachers', methods=['GET'])
@login_required
def teachers():
    """ Search teachers
    """
    q = request.args.get('q')
    page = request.args.get('page')
    try:
        page = int(page)
    except:
        page = 1
    per_page = 20

    if current_user.is_administrator():
        query = User.query.outerjoin(User.role).filter(Role.name == 'Teacher')
    else:
        query = User.query.filter_by(id=current_user.id)
    if q:
        q = "%"+q+"%"
        query = query.filter(or_(User.username.like(q), User.fullname.like(q)))
    pagination = query.paginate(page, per_page, False)
    teachers = [{'id': t.id, 'username': t.username, 'fullname': t.fullname}
                for t in pagination.items]
    return jsonify({
        'status': 'success',
        'data': {
            'pages': pagination.pages,
            'items': teachers,

        }
    })


@edu.route('/students', methods=['GET'])
@login_required
def students():
    """ Search students
    """
    q = request.args.get('q')
    page = request.args.get('page')
    try:
        page = int(page)
    except:
        page = 1
    per_page = 20

    query = User.query.outerjoin(User.role).filter(Role.name == 'Student')
    if q:
        q = "%"+q+"%"
        query = query.filter(or_(User.username.like(q), User.fullname.like(q)))
    pagination = query.paginate(page, per_page, False)
    students = [{'id': s.id, 'username': s.username, 'fullname': s.fullname}
                for s in pagination.items]
    return jsonify({
        'status': 'success',
        'data': {
            'pages': pagination.pages,
            'items': students,
        }
    })


@edu.route('/course/<int:id>/start', methods=['PUT'])
@login_required
def start_course(id):
    result = {
        'status':'success',
        'data': {
            'id':id,
            'capacity':0,
            'msg':'',
            'conflict_lessons':[],
            'lesson':{
                'start_datetime':'',
                'end_datetime':''
            }
        }
    }

    course = Course.query.filter_by(id=id).first()
    if course:
        result['data']['capacity'] = course.capacity
        temp_lesson_form = TempLessonForm()
        now = datetime.datetime.now()

        # 通过创建临时的lesson来手动启动课程
        if temp_lesson_form.validate_on_submit():
            # 根据提交的表单的类型创建课时
            if temp_lesson_form.end_time_type.data == 'period_id':
                end_time = Period.query.get(temp_lesson_form.end_period_id.data)
            else:
                end_time = temp_lesson_form.end_time.data.time()
            lesson = Lesson(course_id=course.id,
                            start_date=now.date(),
                            end_date=temp_lesson_form.end_date.data,
                            _start_time=now.time())
            lesson.end_time = end_time

            conflicts = course.query_lessons(lesson.start_datetime, lesson.end_datetime).all()
            if conflicts:
                LOG.warning('Could not create lesson %s, conflicts with others' % lesson)
                flash('时间段冲突', category='error')
                result['status'] = 'fail'
                result['data']['msg'] = '时间段冲突'
                for lesson in conflicts:
                    result['data']['conflict_lessons'].append({
                        'id': lesson.id,
                        'start_datetime': lesson.start_datetime.strftime("%c"),
                        'end_datetime': lesson.end_datetime.strftime("%c")
                    })
            else:
                # audit resource
                if not ResourceController().audit_schedule_lesson(lesson):
                    flash('资源使用超出系统上限', category='error')
                    LOG.debug('Could not create lesson, resource exceed system limit')
                    result['status'] = 'fail'
                    result['data']['msg'] = 'resource exceed system limit'
                else:
                    db.session.add(lesson)
                    db.session.commit()
                    LOG.info('Create lesson %s of course %s' % (lesson, course))
                    ua_logger.info(current_user, '手动启动课程: %s_%s' % (id, course.name))
    else:
        flash('启动失败：课程不存在', category='error')
        result['status'] = 'fail'
        result['data']['msg'] = 'course not exist'
    return jsonify(result)


@edu.route('/course/delete_conflit_lessons_for_start', methods=['PUT'])
@login_required
def delete_conflict_lessons_for_start():
    request_json = request.json
    conflict_lessons = request_json['conflict_lessons']
    lesson_info = request_json['lesson']
    for item in conflict_lessons:
        conflict_lesson = Lesson.query.filter_by(id=item['id']).first()
        if conflict_lesson:
            db.session.delete(conflict_lesson)

    start_datetime = datetime.datetime.strptime(lesson_info['start_datetime'], "%c")
    end_datetime = datetime.datetime.strptime(lesson_info['end_datetime'], "%c")
    lesson = Lesson(course_id=lesson_info['course_id'],
                    start_date=start_datetime.date(),
                    end_date=end_datetime.date(),
                    start_time=start_datetime.time(),
                    end_time=end_datetime.time()
                    )
    db.session.add(lesson)
    db.session.commit()
    course = Course.query.filter_by(id=lesson_info['course_id']).first()
    return jsonify({
        "status":"success",
        "data":{
            "course_id":lesson_info['course_id'],
            "capacity":course.capacity
        }
    })


@edu.route('/course/<int:id>/stop', methods=['PUT'])
@login_required
def stop_course(id):
    course = Course.query.filter_by(id=id).first()
    if course:
        course.stop()
        LOG.debug("%s(%s) try to stop course %d",
                  current_user.username, current_user.role.name, id)
        ua_logger.info(current_user, "手动终止课程: %s_%s" % (id, course.name))
        return jsonify({'status': 'success',
                        'data': {'id': id,
                                 'capacity': course.capacity}})
    else:
        # flash(
        #     "终止失败：课程不存在",
        #     'error'
        # )
        return jsonify({'status': 'fail',
                        'data': {'id': id,
                                 'msg': 'course not exist'}})


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


@edu.route('/binding_students/<int:id>', methods=['GET'])
@login_required
def binding_students(id):
    """ Search students
    """
    course = Course.query.filter_by(id=id).first()
    q = request.args.get('q')
    page = request.args.get('page')
    try:
        page = int(page)
    except:
        page = 1
    per_page = 20

    query = course.users


    # for desktop in course.desktops:
    #     if desktop.owner_id != None:
    #         query = query.filter(User.id != desktop.owner_id)

    if q:
        q = "%"+q+"%"
        query = query.filter(or_(User.username.like(q), User.fullname.like(q)))

    pagination = query.paginate(page, per_page, False)
    students = [{'id': s.id, 'username': s.username, 'fullname': s.fullname}
                for s in pagination.items]
    return jsonify({
        'status': 'success',
        'data': {
            'pages': pagination.pages,
            'items': students,
        }
    })



