# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# comment
#
# 2016/4/21 chengkang : Init

from app import app, db
from app.models import Role, User, Permission
from flask import url_for
import uuid
import os
import datetime
from app.models import Course, User, SambaAccount, SambaServer
from app.common import password_utils

def create_administrator(username, password, confirmed=True):
    """
    Creator a administrator user for unittest

    @param username: The administrator's username
    @param password: The administrator's password

    """
    role_name = "Administrator"
    admin_role = Role.query.filter_by(name=role_name).first()
    if not admin_role:
        admin_role = Role(name=role_name, description="Administrator", permissions=0x80)
        db.session.add(admin_role)

    admin_user = User.query.filter_by(username=username).first()
    if not admin_user:
        admin_user = User(username=username, fullname=username, role=admin_role, confirmed=confirmed)
        admin_user.password = password
        db.session.add(admin_user)
    db.session.commit()
    return admin_user

def create_administrator(username, password, confirmed=True):
    """
    Creator a administrator user for unittest

    @param username: The administrator's username
    @param password: The administrator's password

    """
    role_name = "Administrator"
    admin_role = Role.query.filter_by(name=role_name).first()
    if not admin_role:
        admin_role = Role(name=role_name, description="Administrator", permissions=0x80)
        db.session.add(admin_role)

    admin_user = User.query.filter_by(username=username).first()
    if not admin_user:
        admin_user = User(username=username, fullname=username, role=admin_role, confirmed=confirmed)
        admin_user.password = password
        db.session.add(admin_user)
    db.session.commit()
    return admin_user


def create_teacher(username, password, confirmed=True):
    """
    Creator a teacher user for unittest

    @param username: The teacher's username
    @param password: The teacher's password

    """
    role_name = "Teacher"
    teacher_role = Role.query.filter_by(name=role_name).first()
    if not teacher_role:
        teacher_role = Role(name=role_name, description="Teacher", permissions=(Permission.COURSE | Permission.DESKTOP))
        db.session.add(teacher_role)

    teacher_user = User.query.filter_by(username=username).first()
    if not teacher_user:
        teacher_user = User(username=username, fullname=username, role=teacher_role, confirmed=confirmed)
        teacher_user.password = password
        db.session.add(teacher_user)
    db.session.commit()
    return teacher_user


def create_student(username, password, confirmed=True):
    """
    Creator a student user for unittest

    @param username: The student's username
    @param password: The student's password

    """
    role_name = "Student"
    student_role = Role.query.filter_by(name=role_name).first()
    if not student_role:
        student_role = Role(name=role_name, description="Student", permissions=(Permission.DESKTOP))
        db.session.add(student_role)

    student_user = User.query.filter_by(username=username).first()
    if not student_user:
        student_user = User(username=username, fullname=username, role=student_role, confirmed=confirmed)
        student_user.password = password
        db.session.add(student_user)
    db.session.commit()
    return student_user


def login_system(client, username, password):
    rv = client.post(url_for('auth.login'), data=dict(username_email=username,
                                                    password=password,
                                                    submit=''), follow_redirects=True)

    if "detectCapsLock" in rv.data.decode("utf-8"):

        # this means login failed
        raise Exception("Login failed")

def logout_system(client):
    rv = client.get(url_for('auth.logout'), follow_redirects=True)

def create_course(coursename, ownername):
    """
    create
    :param: coursename
    :return:
    """
    course = Course(name=coursename)
    course.start_date = datetime.date.today() - datetime.timedelta(days=1)
    course.end_date = datetime.datetime.today() + datetime.timedelta(days=1)
    course.capacity = 4
    course.image_ref = os.environ.get('OS_IMAGE_REF')  # cirros-x86
    course.flavor_ref = os.environ.get('OS_FLAVOR_REF')  # m1.tiny
    course.owner = User.query.filter_by(username=ownername).first()
    db.session.add(course)
    db.session.commit()
    return course

def create_personal_storage(name, ip, administrator, password):
    new_samba_server = SambaServer.query.filter_by(ip=ip).first()
    if not new_samba_server:
        encrypt_pwd = password_utils.encrypt(password)
        new_samba_server = SambaServer()
        new_samba_server.name = name
        new_samba_server.ip = ip
        new_samba_server.administrator = administrator
        new_samba_server.password = encrypt_pwd
        db.session.add(new_samba_server)
    db.session.commit()
    return new_samba_server
