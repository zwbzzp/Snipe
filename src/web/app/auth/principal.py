# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# comment
#
# 4/15/16 lipeizhao : Init

from collections import namedtuple
from functools import partial

from flask.ext.principal import Permission, RoleNeed, TypeNeed

##################
# login user has permissions regarding below role type

# role permissions
admin_permission = Permission(RoleNeed('Administrator'))
teacher_permission = Permission(RoleNeed('Teacher'))
student_permission = Permission(RoleNeed('Student'))

##################
# if login user can operate on below type of objects

# student type permission
StudentTypeNeed = partial(TypeNeed, 'student')
student_type_perm = Permission(StudentTypeNeed())

# teacher type permission
TeacherTypeNeed = partial(TypeNeed, 'teacher')
teacher_type_perm = Permission(TeacherTypeNeed())

# Admin type permission
AdminTypeNeed = partial(TypeNeed, 'admin')
admin_type_perm = Permission(AdminTypeNeed())

# terminal type permission
TerminalTypeNeed = partial(TypeNeed, 'terminal')
terminal_type_perm = Permission(TerminalTypeNeed())

##################
# if login user can operate on below type of objects regarding specific object id

# template resource need
TemplateNeed = namedtuple('template', ['method', 'value'])
TemplateAllNeed = partial(TemplateNeed, 'all')

# course resource need
CourseNeed = namedtuple('course', ['method', 'value'])
CourseAllNeed = partial(CourseNeed, 'all')

# desktop resource need
DesktopNeed = namedtuple('desktop', ['method', 'value'])
DesktopAllNeed = partial(DesktopNeed, 'all')
