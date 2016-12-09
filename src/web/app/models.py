# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# comment
#
# 2016/2/18 fengyc : Init

import datetime
import json
import time
import traceback
import functools
from enum import Enum
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from flask import current_app, request, url_for
from flask.ext.login import UserMixin, AnonymousUserMixin
from flask.ext.sqlalchemy import BaseQuery
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy import case
from sqlalchemy.orm import relationship
from . import login_manager
from . import db

from phoenix.cloud import compute
from phoenix.cloud import image
# from .celery_tasks import run_desktoptask


class IdMixin(object):
    """ ID mixin
    """
    id = db.Column(db.Integer, primary_key=True)


class TimestampMixin(object):
    """ Timestamp mixin
    """
    created_at = db.Column(db.DateTime, default=datetime.datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.now,
                           onupdate=datetime.datetime.now)


class SoftDeleteQuery(BaseQuery):
    def soft_delete(self, synchronize_session='evaluate'):
        return self.update({'deleted': True,
                            'deleted_at': datetime.datetime.now(),
                            }, synchronize_session)


class SoftDeleteMixin(object):
    """ Soft deleted mixin

    SoftDeletedMixin has 3 types of query. `query` do not return soft deleted
    values, `query_all` return all values, and `query_deleted` return only soft
    deleted values.
    """
    deleted = db.Column(db.Boolean, default=False, index=True)
    deleted_at = db.Column(db.DateTime, default=None)
    query_class = SoftDeleteQuery

    def __init__(self, *args, **kwargs):
        super(SoftDeleteMixin, self).__init__(*args, **kwargs)
        # Monkey patch query object to support soft deleted
        if self.query is not None:
            self.query_all = self.query
            self.query_deleted = self.query_all.filter_by(deleted=True)
            self.query = self.query_all.filter_by(deleted=False)

    def soft_delete(self):
        self.deleted = True
        self.deleted_at = datetime.datetime.now()
        db.session.add(self)
        db.session.commit()


class SaveMixin(object):
    def save(self):
        db.session.add(self)
        db.session.commit()


##################
# auth
##################

class Permission:
    COURSE = 0x01
    DESKTOP = 0x02
    ADMINISTER = 0x80


class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    description = db.Column(db.Text)
    permissions = db.Column(db.Integer)
    users = db.relationship('User', backref='role', lazy='dynamic')

    @staticmethod
    def insert_default_roles():
        roles = {
            'Administrator': {
                'permissions': (0x80),
                'description': 'administrator'
            },
            'Teacher': {
                'permissions': (Permission.COURSE | Permission.DESKTOP),
                'description': 'teacher role'
            },
            'Student': {
                'permissions': (Permission.DESKTOP),
                'description': 'student role'
            },
            'Terminal': {
                'permissions': (Permission.DESKTOP),
                'description': 'terminal role'
            }
        }
        for r in roles:
            role = Role.query.filter_by(name=r).first()
            if role is None:
                role = Role(name=r)
            role.permissions = roles[r]['permissions']
            role.description = roles[r]['description']
            db.session.add(role)
        db.session.commit()

    def __repr__(self):
        return '<Role %r>' % self.name


class UserStatus(object):
    INACTIVE = 'INACTIVE'
    ACTIVE = 'ACTIVE'


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, index=True)
    fullname = db.Column(db.String(64), default="")
    email = db.Column(db.String(64), unique=True, index=True)
    is_active = db.Column(db.Boolean, default=True)
    is_device = db.Column(db.Boolean, default=False)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))
    password_hash = db.Column(db.String(128))
    confirmed = db.Column(db.Boolean, default=False)

    terminal = relationship("Terminal", uselist=False, back_populates="user")
    desktops = db.relationship('Desktop', backref='owner')
    own_courses = db.relationship('Course', backref='owner', lazy='dynamic')
    ftps = db.relationship('FtpServer', backref='user', lazy='dynamic')
    samba_accounts = db.relationship('SambaAccount', backref='user', lazy='dynamic')
    images = db.relationship('Image', backref='user', lazy='dynamic')


    # permissions = 0xff

    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    def generate_confirmation_token(self, expiration=3600):
        s = Serializer(current_app.config['SECRET_KEY'], expiration)
        return s.dumps({'confirm': self.id})

    def confirm(self, token):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except:
            return False
        if data.get('confirm') != self.id:
            return False
        self.confirmed = True
        db.session.add(self)
        db.session.commit()
        return True

    def can(self, permissions):
        return self.role.permissions & permissions == permissions

    def is_administrator(self):
        return self.can(Permission.ADMINISTER)

    def is_super_administrator(self):
        return self.username == 'admin'

    def gravatar(self, size=100, default='identicon', rating='g'):
        return ''

    def generate_reset_password_token(self, expiration=3600):
        s = Serializer(current_app.config['SECRET_KEY'], expires_in=expiration)
        return s.dumps({'reset': self.email})

    def reset_password(self, token, password):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except Exception as e:
            return False
        if data.get('reset') != self.email:
            return False
        self.password = password
        db.session.add(self)
        db.session.commit()
        return True


    def generate_auth_token(self, expiration):
        s = Serializer(current_app.config['SECRET_KEY'],
                       expires_in=expiration)
        return s.dumps({'id': self.id}).decode('ascii')

    def __repr__(self):
        return '<User %r>' % self.username

    @staticmethod
    def verify_auth_token(token):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except:
            return None
        return User.query.get(data['id'])

    def get_desktop(self, desktop_id):
        for desktop in self.desktops:
            if desktop.id == desktop_id:
                return desktop
        return None

    @staticmethod
    def insert_default_users():
        users = {
            'admin': {
                'email': 'admin@example.com',
                'password': 'admin123',
                'role': 'Administrator',
            },
            'teacher': {
                'email': 'teacher@example.com',
                'password': 'admin123',
                'role': 'Teacher',
            },
            'student': {
                'email': 'student@example.com',
                'password': 'admin123',
                'role': 'Student',
            }
        }
        for u in users:
            user = User.query.filter_by(username=u).first()
            if user is None:
                user = User(username=u, fullname=u, email=users[u]['email'], is_active=True, confirmed=True)
                user.password = users[u]['password']
                user.role = Role.query.filter_by(name=users[u]['role']).first()
            db.session.add(user)
        db.session.commit()


class AnonymousUser(AnonymousUserMixin):
    def can(self, permissions):
        return False

    def is_administrator(self):
        return False

login_manager.anonymous_user = AnonymousUser


@login_manager.user_loader
def load_user(user_id):
    # user_id is a unicode string, needed to be converted it to int
    return User.query.get(int(user_id))


##################
# celery
##################

from .celery_sqlalchmey_scheduler_models import CrontabSchedule,\
    IntervalSchedule, DatabaseSchedulerEntry


#################
# cloud
#################


class Image(db.Model, IdMixin, TimestampMixin):
    __tablename__ = 'images'
    name = db.Column(db.String(64))
    ref_id = db.Column(db.String(64))
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    description = db.Column(db.String(256), default='')
    visibility = db.Column(db.String(10), default='public')

    @staticmethod
    def insert_all_images():
        user = User.query.filter_by(username='admin').first()
        if not user:
            raise
        imgs = image.list_images()
        for p in imgs:
            img = Image.query.filter_by(ref_id=p.id).first()
            if img is None:
                img = Image()
                img.ref_id = p.id
                img.name = p.name
                img.owner_id = user.id
            db.session.add(img)
        db.session.commit()

    def __repr__(self):
        return '<Image %r>' % self.ref_id


class Flavor(db.Model, IdMixin, TimestampMixin):
    __tablename__ = 'flavors'
    ref_id = db.Column(db.String(64))
    name = db.Column(db.String(64))
    description = db.Column(db.String(64))

    @staticmethod
    def insert_all_flavors():
        flavors = compute.list_flavors()
        for p in flavors:
            flavor = Flavor.query.filter_by(ref_id=p.id).first()
            if flavor is None:
                flavor = Flavor()
                flavor.ref_id = p.id
                flavor.name = p.name
                flavor.description = "%dCPU | %dM RAM | %dG Disk" % (p.vcpus, p.ram,p.disk)
            db.session.add(flavor)
        db.session.commit()

    def __repr__(self):
        return '<Image %r>' % self.name


class Protocol(db.Model, IdMixin, TimestampMixin):
    __tablename__ = 'protocols'
    name = db.Column(db.String(64))

    @staticmethod
    def insert_all_protocols():
        protocols = {
            'vRay': {
            },
            'rdp': {
            }
        }
        for p in protocols:
            protocol = Protocol.query.filter_by(name=p).first()
            if protocol is None:
                protocol = Protocol(name=p)
            db.session.add(protocol)
        db.session.commit()


#################
# schedule
#################

class DesktopType(object):
    """ Desktop types
    """
    COURSE = 'COURSE'
    STATIC = 'STATIC'
    FREE = 'FREE'
    TEMPLATE = 'TEMPLATE'

    @staticmethod
    def get_type_chs(desktop_type):
        type_dict = {DesktopType.COURSE: "课程桌面",
                     DesktopType.STATIC: "固定桌面",
                     DesktopType.FREE: "浮动桌面",
                     DesktopType.TEMPLATE: "镜像实例"}
        return type_dict.get(desktop_type, desktop_type)


class DesktopState(object):
    BUILDING = 'BUILDING'
    ACTIVE = 'ACTIVE'
    SPAWNING = "SPAWNING"
    SUSPENDING = "SUSPENDING"
    SUSPENDED = "SUSPENDED"
    STARTING = "STARTING"
    USING = "USING"
    ERROR = "ERROR"
    SNAPSHOTING = "SNAPSHOTING"
    REBOOTING = "REBOOTING"
    SNAPSHOTERROR = "SNAPSHOTERROR"
    DELETING = "DELETING"
    MANUALSTART = "MANUALSTART"
    SHUTOFF = "SHUTOFF"
    STOPPING ="STOPPING"
    REBUILDING = "REBUILDING"
    BUILD ="BUILD"
    MIGRATING = "MIGRATING"
    EVACUATING = "EVACUATING"

    @staticmethod
    def get_state_chs(desktop_state):
        state_dict = {
            DesktopState.BUILD: "创建中",
            DesktopState.BUILDING: "创建中",
            DesktopState.ACTIVE:  "已启动",
            DesktopState.SPAWNING: "创建中",
            DesktopState.SUSPENDING:"挂起中",
            DesktopState.SUSPENDED: "挂起",
            DesktopState.STARTING: "正在启动",
            DesktopState.USING: "正在使用中",
            DesktopState.ERROR: "异常",
            DesktopState.SNAPSHOTING: "创建快照中",
            DesktopState.REBOOTING: "重启中",
            DesktopState.SNAPSHOTERROR: "快照创建异常",
            DesktopState.DELETING: "删除中",
            DesktopState.MANUALSTART: "正在启动",
            DesktopState.SHUTOFF: "关机",
            DesktopState.REBUILDING: "重建中",
            DesktopState.STOPPING: "正在关机",
            DesktopState.MIGRATING:"迁移中",
            DesktopState.EVACUATING:"撤离中",
        }
        return state_dict.get(desktop_state, desktop_state)


class TaskAction(object):
    CREATE = 'CREATE'
    DELETE = 'DELETE'
    DELAY = 'DELAY'
    STOP = 'STOP'
    START = 'START'
    REBOOT = 'REBOOT'
    REBUILD = 'REBUILD'
    SUSPEND = 'SUSPEND'
    RESUME = 'RESUME'
    SNAPSHOT = 'SNAPSHOT'
    MIGRATE = 'MIGRATE'
    EVACUATE = 'EVACUATE'


class TaskState(object):
    PENDING = 'PENDING'
    RUNNING = 'RUNNING'
    FINISHED = 'FINISHED'
    DEPRECATED = 'DEPRECATED' # for task that only for history record

    @staticmethod
    def get_state_chs(task_state):
        state_dict = {
            TaskState.PENDING: "等待执行",
            TaskState.RUNNING: "正在执行",
            TaskState.FINISHED: "成功执行"
        }
        return state_dict.get(task_state, task_state)


class TaskResult(object):
    SUCCESS = 'SUCCESS'
    ERROR = 'ERROR'

    @staticmethod
    def get_state_chs(task_result):
        state_dict = {
            TaskResult.ERROR: "执行失败",
            TaskResult.SUCCESS: "成功执行"
        }
        return state_dict.get(task_result, task_result)


class StageResult(db.Model, IdMixin, TimestampMixin):
    """ Stage result of desktop task
    """
    __tablename__ = 'stage_results'
    task_id = db.Column(db.Integer, db.ForeignKey('desktop_tasks.id'))
    stage = db.Column(db.String(64), default='')
    success = db.Column(db.Boolean, default=True)
    detail = db.Column(db.String(5000), default='')
    context = db.Column(db.Text, default=json.dumps({}))

    def __repr__(self):
        result = 'success' if self.success else 'failed'
        return '<StageResult %r:%s>' % (self.stage, result)


class DesktopTask(db.Model, IdMixin, TimestampMixin):
    """ Desktop task

    Desktop task is the core context of scheduling.
    """
    __tablename__ = 'desktop_tasks'
    action = db.Column(db.String(16), default=TaskAction.CREATE, index=True)
    state = db.Column(db.String(16), default=TaskState.PENDING, index=True)
    result = db.Column(db.String(16), default='', index=True)
    stage = db.Column(db.String(64), default='')
    stage_chain = db.Column(db.Text, default=json.dumps([]))
    retries = db.Column(db.Integer, default=0)
    enabled = db.Column(db.Boolean, default=True)
    context = db.Column(db.Text, default=json.dumps({}))

    stage_results = db.relationship(StageResult, order_by='StageResult.created_at',
                                    backref='task', lazy='dynamic')

    def __getitem__(self, item):
        if not hasattr(self, '__ctx'):
            self.__ctx = json.loads(self.context)
        return self.__ctx[item]

    def __setitem__(self, key, value):
        if not hasattr(self, '__ctx'):
            self.__ctx = json.loads(self.context)
        self.__ctx[key] = value
        self.context = json.dumps(self.__ctx)

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def resume(self):
        """ Continue the task from the fail stage
        """
        # reset task attributes
        self.state = TaskState.RUNNING
        self.result = None
        self.context = self.pre_stage_context()
        self.retries = 0
        db.session.add(self)
        db.session.commit()

    def reset(self):
        """ Reset the task to the initial state
        """
        self.state = TaskState.PENDING
        self.result = None
        self.stage = self.first_stage
        self.context = self.first_stage_context()
        self.retries = 0
        db.session.add(self)
        db.session.commit()

    def enable(self):
        """ Enable the task
        """
        self.enabled = True
        db.session.add(self)
        db.session.commit()

    def disable(self):
        """ Disable the task
        """
        self.enabled = False
        db.session.add(self)
        db.session.commit()

    def deprecate(self):
        """ Deprecate the task
        """
        self.state = TaskState.DEPRECATED
        db.session.add(self)
        db.session.commit()

    def record_stage(self, is_success=True, detail=''):
        """ Record stage result of the task
        """
        stage_result = StageResult()
        stage_result.task = self
        stage_result.stage = self.stage
        stage_result.success = is_success
        if detail:
            stage_result.detail = detail
        else:
            stage_result.detail = traceback.format_exc() if not is_success else None
        stage_result.context = self.context
        db.session.add(stage_result)
        db.session.commit()

    @property
    def first_stage(self):
        """ Get first stage
        """
        chain = json.loads(self.stage_chain)
        return chain[0]

    def pre_stage_context(self):
        for stage_result in self.stage_results:
            if stage_result.stage == self.pre_stage:
                return stage_result.context
        return None

    def first_stage_context(self):
        for stage_result in self.stage_results:
            if stage_result.stage == self.first_stage:
                return stage_result.context
        return None

    @property
    def pre_stage(self):
        """ Get last stage
        """
        chain = json.loads(self.stage_chain)
        idx = chain.index(self.stage)
        if idx <= 1:
            return chain[0]
        return chain[idx-1]

    @property
    def next_stage(self):
        """ Get next stage
        """
        chain = json.loads(self.stage_chain)
        idx = chain.index(self.stage)
        if idx + 1 < len(chain):
            return chain[idx+1]
        return None

    def set_running(self):
        if self.state != TaskState.FINISHED:
            self.state = TaskState.RUNNING

    def go_error(self, detail=''):
        """ Update task as error
        """
        self.state = TaskState.FINISHED
        self.result = TaskResult.ERROR
        db.session.add(self)
        db.session.commit()

    def go_next(self):
        """ Update task to next stage or success
        """
        next_stage = self.next_stage
        if next_stage is not None:
            self.retries = 0
            self.stage = next_stage
        else:
            self.state = TaskState.FINISHED
            self.result = TaskResult.SUCCESS
        db.session.add(self)
        db.session.commit()

    def __repr__(self):
        return '<DesktopTask %r>' % self.id

#################
# edu
#################


class Place(db.Model, IdMixin, TimestampMixin):
    __tablename__ = 'places'
    name = db.Column(db.String(64))
    address = db.Column(db.String(256))

    terminals = db.relationship('Terminal', backref='place', lazy='dynamic')

    def __repr__(self):
        return '<Place %r>' % self.name

    def to_json(self):
        return {'name': self.name,
                'address': self.address}

class Period(db.Model, IdMixin, TimestampMixin):
    __tablename__ = 'periods'
    name = db.Column(db.String(64))
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)

    def __repr__(self):
        return '<Period %r>' % self.name

    @staticmethod
    def insert_default_periods():
        Period.query.delete()
        # insert default period, from 6:00 - 20:00
        start_time = datetime.time(hour=6)
        day_end_time = datetime.time(hour=20)
        duration = datetime.timedelta(minutes=40)
        i = 1
        while start_time < day_end_time:
            end_time = (datetime.datetime.combine(datetime.date.today(), start_time) + duration).time()
            period = Period(name=str(i), start_time=start_time, end_time=end_time)
            db.session.add(period)
            i += 1
            start_time = end_time
        db.session.commit()

    @staticmethod
    def find_conflicts(period):
        """ 查找时间冲突的时间段
        :param period: 待测试的时间段
        :return:
        """
        query = Period.query.filter(db.or_(
            db.and_(Period.start_time <= period.start_time, Period.end_time >= period.end_time),
            db.or_(
                db.and_(Period.start_time <= period.start_time, Period.end_time >= period.start_time),
                db.and_(Period.start_time <= period.end_time, Period.end_time >= period.end_time)
            )
        ))
        if period.id is not None:
            query.filter(Period.id != period.id)
        return query.all()

    def update_lessons(self, skip_conficts=True):
        """ 更新 lesson 对时间段的引用
        :return:
        """
        now = datetime.datetime.now()
        with db.session.begin(subtransactions=True):
            # 第一阶段,如果课时已开始,或者已结束,那么直接设置为 None
            start_query = Lesson.query.filter(Lesson.start_period_id == self.id)
            start_query = start_query.filter(db.or_(
                Lesson.start_date < now.date(),
                db.and_(Lesson.start_date == now.date(), Lesson._start_time <= now.time())))
            start_query.update({Lesson.start_period_id: None})
            # 已结束的课时
            end_query = Lesson.query.filter(Lesson.end_period_id == self.id)
            end_query = end_query.filter(db.or_(
                Lesson.end_date < now.date(),
                db.and_(Lesson.end_date == now.date(), Lesson._end_time <= now.time())
            ))
            end_query.update({Lesson.end_period_id: None})

            # 第二阶段,直接更新已有时间
            start_query = Lesson.query.filter(Lesson.start_period_id == self.id)
            start_query.update({Lesson._start_time: self.start_time})
            end_query = Lesson.query.filter(Lesson.end_period_id == self.id)
            end_query.update({Lesson._end_time: self.end_time})

    def delete_lessons(self):
        """ 删除引用本时间段的 lesson

        在删除本时段前,应先删除相应的 lesson
        :return:
        """
        now = datetime.datetime.now()
        with db.session.begin(subtransactions=True):
            # 第一阶段,找到所有已开始的课程,直接设置为 None
            # 开始时间引用本时段
            start_query = Lesson.query.filter(Lesson.start_period_id == self.id)
            start_query = start_query.filter(db.or_(
                Lesson.start_date < now.date(),
                db.and_(Lesson.start_date == now.date(), Lesson._start_time <= now.time())
            ))
            start_query.update({Lesson.start_period_id: None})
            # 结束时间引用本时段,且已在运行,那么也直接设置为 None,继续按照原有时间运行
            end_query = Lesson.query.filter(Lesson.end_period_id == self.id)
            end_query = end_query.filter(db.or_(
                Lesson.start_date < now.date(),
                db.and_(Lesson.start_date == now.date(), Lesson._start_time <= now.time())
            ))
            end_query.update({Lesson.end_period_id: None})

            # 第二阶段,其它情况下,直接删除
            query = Lesson.query.filter(db.or_(
                Lesson.start_period_id == self.id,
                Lesson.end_period_id == self.id
            ))
            query.delete()

    @staticmethod
    def refresh_names():
        periods = Period.query.order_by(db.asc(Period.start_time))
        idx = 1
        for p in periods:
            p.name = idx
            idx += 1
        db.session.add_all(periods)
        db.session.commit()

course_selection_table = db.Table('course_selections',
    db.Column('course_id', db.Integer, db.ForeignKey('courses.id', ondelete='CASCADE', onupdate='CASCADE'), nullable=False),
    db.Column('user_id', db.Integer, db.ForeignKey('users.id', ondelete='CASCADE', onupdate='CASCADE'), nullable=False),
    db.PrimaryKeyConstraint('course_id', 'user_id'))

course_place_table = db.Table('course_place',
    db.Column('course_id', db.Integer, db.ForeignKey('courses.id', ondelete='CASCADE', onupdate='CASCADE'), nullable=False),
    db.Column('place_id', db.Integer, db.ForeignKey('places.id', ondelete='CASCADE', onupdate='CASCADE'), nullable=False),
    db.PrimaryKeyConstraint('course_id', 'place_id'))


class Course(db.Model, IdMixin, TimestampMixin):
    __tablename__ = 'courses'
    name = db.Column(db.String(64), nullable=False)  # FIXME no space allowed
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    capacity = db.Column(db.Integer, default=0)

    image_ref = db.Column(db.String(64))
    flavor_ref = db.Column(db.String(64))
    network_ref = db.Column(db.String(64))
    protocol = db.Column(db.String(64))

    policy_id =  db.Column(db.Integer, db.ForeignKey('policies.id'))
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    # owner = db.relationship('User')

    lessons = db.relationship('Lesson', backref='course', cascade="all, delete-orphan", lazy='dynamic')
    desktops = db.relationship('Desktop', backref='course', lazy='dynamic')
    users = db.relationship('User', secondary=course_selection_table, backref='courses', lazy='dynamic')

    places = db.relationship('Place',
                            secondary=course_place_table,
                            backref=db.backref('courses', lazy='dynamic'),
                            lazy='dynamic')
    ftp_accounts = db.relationship('FtpAccount', backref='course', lazy='dynamic')

    @property
    def students(self):
        return self.users.filter(db.or_(User.is_device==None, User.is_device == False)).all()

    @property
    def terminal_users(self):
        return self.users.filter(User.is_device == True).all()

    def delay(self, latency=900):
        """ Delay desktops of the course
        """
        lesson = self.find_current_lesson()
        if not lesson:
            raise Exception("Unable to delay course %r due to having no current lesson" % self)
        lesson.delay(latency)
        for desktop in self.desktops:
            desktop.delay(latency)
        return self.desktops.count()

    def find_current_lesson(self, current_datetime=None):
        """ Get current lesson of the course
        :param current_datetime: current datetime
        :return: lesson or None
        """
        if not current_datetime:
            current_datetime = datetime.datetime.now()
        query = Lesson.query.filter(Lesson.course_id == self.id)
        query = query.filter(db.and_(
            db.or_(Lesson.start_date < current_datetime.date(),
                   db.and_(Lesson.start_date == current_datetime.date(),
                           Lesson._start_time <= current_datetime.time()))),
            db.or_(Lesson.end_date > current_datetime.date(),
                   db.and_(Lesson.end_date == current_datetime.date(),
                           Lesson._end_time >= current_datetime.time())))
        query = query.order_by(db.desc(Lesson.end_date), db.desc(Lesson._end_time))
        return query.first()

    def find_conflict_lessons(self, start_datetime, end_datetime):
        conflicts = []
        for lesson in self.query_lessons(start_datetime, end_datetime):
            max_start_datetime = max(lesson.start_datetime, start_datetime)
            min_end_datetime = min(lesson.end_datetime, end_datetime)
            if (min_end_datetime - max_start_datetime).total_seconds() > 0:
                conflicts.append(lesson)
        return conflicts

    @functools.lru_cache(maxsize=1)
    def query_lessons(self, start_datetime, end_datetime):
        """ Find lessons running between start and end
        :param start_datetime: start datetime
        :param end_datetime: end datetime
        :return: list of lessons
        """
        assert start_datetime is not None
        assert end_datetime is not None
        query = Lesson.query.filter(Lesson.course_id == self.id)
        query = query.filter(db.and_(
            db.or_(Lesson.start_date < end_datetime.date(),
                   db.and_(Lesson.start_date == end_datetime.date(),
                           Lesson._start_time <= end_datetime.time())),
            db.or_(Lesson.end_date > start_datetime.date(),
                   db.and_(Lesson.end_date == start_datetime.date(),
                           Lesson._end_time >= start_datetime.time()))
        ))
        return query

    def supply_desktops(self, count=1):
        from .celery_tasks import run_desktoptask
        current_lesson = self.find_current_lesson()
        if current_lesson:
            tasks = []
            for i in range(count):
                current_serial = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                task = DesktopTask()
                task.state = 'PENDING'
                task.stage_chain = json.dumps(['BUILD', 'WAIT', 'FLOATING', 'DETECT'])
                task.stage = 'BUILD'
                task.context = json.dumps({
                    'course': self.id,
                    'course_name': self.name,
                    'serial': current_serial,
                    'start_datetime': current_lesson.start_datetime.isoformat(),
                    'end_datetime': current_lesson.end_datetime.isoformat(),
                    'flavor': self.flavor_ref,
                    'image': self.image_ref,
                    'network': self.network_ref,
                    'desktop_type': DesktopType.COURSE,
                    'subnet': None,
                    'port': None,
                    'disk': None,
                    'wait_state': 'ACTIVE',
                    'wait_timeout': 10*60,
                    'floating_action': 'ASSIGN',
                    'detect_method': 'PING',
                    'detect_timeout': 30,
                    'desktop_state_map': {
                        TaskResult.SUCCESS: DesktopState.ACTIVE,
                        TaskResult.ERROR: DesktopState.ERROR
                    }
                })
                db.session.add(task)
                tasks.append(task)
            db.session.commit()
            # db.session.flush()
            for task in tasks:
                run_desktoptask(task_id=task.id)
        else:
            raise Exception(
                "Unable to supply %s desktops for course %s due to having no current lesson" %
                (count, self))

    def check_conflicts(self, lesson):
        """ 检查是否存在 lesson 时间冲突
        :param lesson: 待检查的 lesson
        :return:
        """
        conflicts = []
        for l in self.lessons:
            if l.id == lesson.id:
                continue
            if l.start_datetime >= lesson.end_datetime or l.end_datetime <= lesson.start_datetime:
                continue
            conflicts.append(l)
        return conflicts

    def stop(self):
        """Stop desktops of the course
        """

        # stop lesson(set lesson end time to time now and scheduled flag to true)
        now = datetime.datetime.now()
        lessons = self.lessons
        current_lesson = None
        for lesson in lessons:
            if lesson.start_datetime < now and lesson.end_datetime > now:
                current_lesson = lesson
                break

        if current_lesson:
            current_lesson.stop()

        # stop course desktops
        for desktop in self.desktops:
            desktop.stop()
        return self.desktops.count()

    def __repr__(self):
        return '<Course %r %r>' % (self.id, self.name)


class Lesson(db.Model, IdMixin, TimestampMixin):
    """ Lesson of course

    Lesson have start datetime and end datetime. Each datetime is combined with
    a `date` field (start_date or end_date) and a `time` field (period_id or a
    customize time).
    """
    __tablename__ = 'lessons'
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id', ondelete='CASCADE', onupdate='CASCADE'))

    start_date = db.Column(db.Date, nullable=False, index=True)
    start_period_id = db.Column(db.Integer, db.ForeignKey('periods.id'))
    start_period = db.relationship(Period, foreign_keys=[start_period_id])
    _start_time = db.Column(db.Time, name='start_time')

    end_date = db.Column(db.Date, nullable=False, index=True)
    end_period_id = db.Column(db.Integer, db.ForeignKey('periods.id'))
    end_period = db.relationship(Period, foreign_keys=[end_period_id])
    _end_time = db.Column(db.Time, name='end_time')

    scheduled = db.Column(db.Boolean, default=False, index=True)
    scheduled_at = db.Column(db.DateTime)
    started = db.Column(db.Boolean, default=False)

    def delay(self, latency=900):
        """ 延长上课时间
        :param latency: 延时
        :return:
        """
        self.end_datetime = self.end_datetime + datetime.timedelta(seconds=latency)
        if self.course.check_conflicts(self):
            raise Exception("Unable to delay lesson %s due to conflict" % self)
        db.session.add(self)

    def stop(self):
        self.end_date =  datetime.date.today()
        self.end_time = datetime.datetime.now()
        db.session.add(self)
        db.session.commit()

    @property
    def start_time(self):
        if self.start_period is not None:
            return self.start_period.start_time
        return self._start_time

    @start_time.setter
    def start_time(self, time_or_period):
        if type(time_or_period) == Period:
            self.start_period = time_or_period
            self._start_time = self.start_period.start_time
        else:
            self.start_period = None
            self._start_time = time_or_period

    @property
    def end_time(self):
        if self.end_period is not None:
            return self.end_period.end_time
        return self._end_time

    @end_time.setter
    def end_time(self, time_or_period):
        if type(time_or_period) == Period:
            self.end_period = time_or_period
            self._end_time = self.end_period.end_time
        else:
            self.end_period = None
            self._end_time = time_or_period

    @property
    def start_datetime(self):
        return datetime.datetime.combine(self.start_date, self.start_time)

    @start_datetime.setter
    def start_datetime(self, start_datetime):
        self.start_date = start_datetime.date()
        self.start_time = start_datetime.time()

    @property
    def end_datetime(self):
        return datetime.datetime.combine(self.end_date, self.end_time)

    @end_datetime.setter
    def end_datetime(self, end_datetime):
        self.end_date = end_datetime.date()
        self.end_time = end_datetime.time()

    @staticmethod
    def query_lessons(start_datetime, end_datetime, exclude_lessons):
        """ Find lessons running between start and end, but excluding lessons with id in exclude_lessons
        :param start_datetime: start datetime
        :param end_datetime: end datetime
        :return: list of lessons
        """
        assert start_datetime is not None
        assert end_datetime is not None
        query = Lesson.query.filter(db.not_(Lesson.id.in_(exclude_lessons)))
        query = query.filter(db.or_(
            db.and_(
                db.or_(Lesson.start_date < start_datetime.date(),
                       db.and_(Lesson.start_date == start_datetime.date(),
                               Lesson._start_time < start_datetime.time())),
                db.or_(Lesson.end_date > start_datetime.date(),
                       db.and_(Lesson.end_date == start_datetime.date(),
                               Lesson._end_time > start_datetime.time()))),
            db.and_(
                db.or_(Lesson.start_date < end_datetime.date(),
                       db.and_(Lesson.start_date == end_datetime.date(),
                               Lesson._start_time < end_datetime.time())),
                db.or_(Lesson.end_date > end_datetime.date(),
                       db.and_(Lesson.end_date == end_datetime.date(),
                               Lesson._end_time > end_datetime.time()))),
            db.and_(
                db.or_(Lesson.start_date > start_datetime.date(),
                       db.and_(Lesson.start_date == start_datetime.date(),
                               Lesson._start_time > start_datetime.time())),
                db.or_(Lesson.end_date < end_datetime.date(),
                       db.and_(Lesson.end_date == end_datetime.date(),
                               Lesson._end_time < end_datetime.time()))
            )))
        return query

    def __repr__(self):
        return '<Lesson %r>' % ((self.start_datetime, self.end_datetime),)


class Pool(db.Model, IdMixin, TimestampMixin):
    __tablename__ = 'pools'
    name = db.Column(db.String(64))


# class VM_STATE():
#     ACTIVE = 'ACTIVE'
#     ERROR = 'ERROR'


# class DESKTOP_STATE():
#     BUILDING = 'BUILDING'
#     ACTIVE = 'ACTIVE'
#     DELETEING = 'DELETING'
#     DELETED = 'DELETED'


class Desktop(db.Model, IdMixin, TimestampMixin):

    class TYPE():
        COURSE = 'COURSE'
        STATIC = 'STATIC'

    class VM_STATE():
        ACTIVE = 'ACTIVE'
        ERROR = 'ERROR'

    __tablename__ = 'desktops'
    name = db.Column(db.String(64))
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'))

    vm_ref = db.Column(db.String(64))     # Cloud vm ref
    vm_state = db.Column(db.String(64), default='', index=True)
    os_state = db.Column(db.String(64), default='', index=True)
    desktop_state = db.Column(db.String(16), default='', index=True)
    desktop_type = db.Column(db.String(16), default='')
    image_ref = db.Column(db.String(64))
    flavor_ref = db.Column(db.String(64))
    floating_ip = db.Column(db.String(64))
    fixed_ip = db.Column(db.String(64))
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    need_floating = db.Column(db.Boolean, default=True, index=True)
    start_datetime = db.Column(db.DateTime)
    end_datetime = db.Column(db.DateTime)

    def __repr__(self):
        if self.course is not None:
            return '<%r %r:%r>' % (self.__class__, self.id,
                                   (self.vm_ref, self.course))
        return '<%r %r:%r>' % (self.__class__, self.id, self.vm_ref)

    def go_active(self):
        self.desktop_state = DesktopState.ACTIVE
        db.session.add(self)
        db.session.commit()

    # desktop operations
    def delay(self, latency=600):
        end_time = self.end_datetime + datetime.timedelta(seconds=latency)
        self.end_datetime = end_time
        db.session.add(self)
        db.session.commit()

    def stop(self):
        end_time = datetime.datetime.now()
        self.end_datetime = end_time
        db.session.add(self)
        db.session.commit()

    def resume(self, async=False):
        compute.resume_server(self.vm_ref)
        if not async:
            Desktop._check_desktop_status(self.vm_ref, ['SUSPENDED'])
        return True

    def reboot(self, async=False):
        compute.reboot_server(self.vm_ref)
        if not async:
            Desktop._check_desktop_status(self.vm_ref, ['ACTIVE'])
        return True

    def shutdown(self, async=False):
        compute.stop_server(self.vm_ref)
        if not async:
            Desktop._check_desktop_status(self.vm_ref, ['SHUTOFF'])
        return True

    @staticmethod
    def _check_desktop_status(server_id, status, time_out=30, sleep_time=2):
        sleep_time = sleep_time
        time_out = time_out
        time_pass = 0
        while time_pass < time_out:
            server_get = compute.get_server(server_id)
            if server_get.status in status:
                return True
            time_pass += sleep_time
            time.sleep(sleep_time)
        # FIXME: Exception too board, should use custom defined Exception instead
        raise Exception('Trace desktop status timeout.')

    def can_reboot_or_del(self):
        '''
        The desktop can reboot or delete or not
        '''
        reboot_and_del_status = [DesktopState.ACTIVE, DesktopState.SUSPENDED,
                                 DesktopState.SHUTOFF, DesktopState.USING]

        if self.desktop_state in reboot_and_del_status:
            return True
        else:
            return False

    def can_rent_or_snap(self):
        '''
        The desktop can rent or snapshot or not(是否可以续租)
        '''
        rs_status = [DesktopState.ACTIVE, DesktopState.USING]
        if self.desktop_state in rs_status:
            return True
        else:
            return False

    def can_rebuild(self):
        '''
        The desktop can be rebuild or not(是否可以重建)
        '''
        disable_status = [DesktopState.SPAWNING,
                          DesktopState.DELETING,
                          DesktopState.SNAPSHOTING,
                          DesktopState.REBUILDING]
        if self.desktop_state not in disable_status:
            return True
        else:
            return False

    def can_power_off(self):
        '''
        The desktop can be poweroffed or not(是否可以关机)
        '''
        available_status = [DesktopState.ACTIVE, DesktopState.USING]
        if self.desktop_state in available_status:
            return True
        else:
            return False

    def can_power_on(self):
        '''
        The desktop can be poweroffed or not(是否可以关机)
        '''
        if self.desktop_state == DesktopState.SUSPENDED:
            return True
        else:
            return False

    def can_migrate_or_evacuate(self):
        if self.desktop_state == DesktopState.ACTIVE:
            return True
        else:
            return False



#################
# settings
#################


class Parameter(db.Model, IdMixin, TimestampMixin):

    class DataType():
        STRING = 'string'
        NUMBER = 'number'
        DATE = 'date'
        BOOLEAN ='bool'

    __tablename__ = 'parameters'
    name = db.Column(db.String(64), unique=True, index=True)
    value = db.Column(db.String(64))
    type = db.Column(db.String(64))
    group = db.Column(db.String(64))
    description = db.Column(db.String(64))


    @staticmethod
    def insert_default_params():
        params = {
            'authentication_URL': {
                'value': 'http://172.18.215.7:5000/v2.0',
                'description': '云平台认证URL',
                'group': 'default',
                'type': Parameter.DataType.STRING
            },
            'authentication_tenant': {
                'value': 'demo',
                'description': '云平台租户',
                'group': 'default',
                'type': Parameter.DataType.STRING
            },
            'authentication_account': {
                'value': 'admin',
                'description': '云平台用户账号',
                'group': 'default',
                'type': Parameter.DataType.STRING
            },
            'authentication_passwd': {
                'value': 'admin123',
                'description': '云平台用户密码',
                'group': 'default',
                'type': Parameter.DataType.STRING
            },
            'IP_address': {
                'value': '172.18.215.7',
                'description': '管理系统IP地址',
                'group': 'default',
                'type': Parameter.DataType.STRING
            },
            'default_protocol': {
                'value': "vRay",
                'description': '默认协议',
                'group': 'system',
                'type': Parameter.DataType.STRING
            },
            'default_policy': {
                'value': "default",
                'description': '默认外设策略',
                'group': 'system',
                'type': Parameter.DataType.STRING
            },
            'free_desktop_switch': {
                'value': "off",
                'description': '自由上机开关',
                'group': 'free_desktop',
                'type': Parameter.DataType.STRING
            },
            'free_desktop_capacity': {
                'value': 20,
                'description': '自由上机容量',
                'group': 'free_desktop',
                'type': Parameter.DataType.NUMBER
            },
            'free_desktop_flavor': {
                'value': None,
                'description': '自由上机桌面配置',
                'group': 'free_desktop',
                'type': Parameter.DataType.STRING
            },
            'free_desktop_image': {
                'value': None,
                'description': '自由上机镜像',
                'group': 'free_desktop',
                'type': Parameter.DataType.STRING
            },
            'free_desktop_start_time': {
                'value': "00:00",
                'description': '自由上机开始时间',
                'group': 'free_desktop',
                'type': Parameter.DataType.STRING
            },
            'free_desktop_stop_time': {
                'value': "23:59",
                'description': '自由上机结束时间',
                'group': 'free_desktop',
                'type': Parameter.DataType.STRING
            },
            'terminal_register_mode': {
                'value': 'APPROVED',
                'description': '客户端注册模式',
                'group': 'terminal',
                'type': Parameter.DataType.STRING
            },
            'course_schedule_ahead': {
                'value': '10',
                'description': '提前开启课程桌面时间',
                'group': 'course_desktop',
                'type': Parameter.DataType.NUMBER
            },
            'course_schedule_latency': {
                'value': '1',
                'description': '延迟关闭课程桌面时间',
                'group': 'course_desktop',
                'type': Parameter.DataType.NUMBER
            },
            'vmotion_notification_email': {
                'value': '',
                'description': '自动通知邮箱',
                'group': 'vmotion',
                'type': Parameter.DataType.STRING
            },
            'vmotion_auto_evacuation': {
                'value': 'on',
                'description': '宕机自动撤离',
                'group': 'vmotion',
                'type': Parameter.DataType.STRING
            }

        }
        for p in params:
            param = Parameter.query.filter_by(name=p).first()
            if param is None:
                param = Parameter(name=p, value=params[p]['value'], description=params[p]['description'], group=params[p]['group'])
                param.type = params[p]['type']
            else:
                param.description = params[p]['description']
                param.group = params[p]['group']
                param.type = params[p]['type']
            db.session.add(param)
        db.session.commit()

    @staticmethod
    def insert_default_free_desktop_params():
        params = {
            'free_desktop_switch': {
                'value': "False",
                'description': '自由上机开关',
                'group': 'free_desktop',
                'type': Parameter.DataType.STRING
            },
            'free_desktop_capacity': {
                'value': 20,
                'description': '自由上机容量',
                'group': 'free_desktop',
                'type': Parameter.DataType.NUMBER
            },
            'free_desktop_flavor': {
                'value': None,
                'description': '自由上机桌面配置',
                'group': 'free_desktop',
                'type': Parameter.DataType.STRING
            },
            'free_desktop_image': {
                'value': None,
                'description': '自由上机镜像',
                'group': 'free_desktop',
                'type': Parameter.DataType.STRING
            },
            'free_desktop_start_time': {
                'value': "00:00",
                'description': '自由上机开始时间',
                'group': 'free_desktop',
                'type': Parameter.DataType.STRING
            },
            'free_desktop_stop_time': {
                'value': "23:59",
                'description': '自由上机结束时间',
                'group': 'free_desktop',
                'type': Parameter.DataType.STRING
            }
        }
        for p in params:
            param = Parameter.query.filter_by(name=p).first()
            if param is None:
                param = Parameter(name=p, value=params[p]['value'], description=params[p]['description'], group=params[p]['group'])
                param.type = params[p]['type']
            db.session.add(param)
        db.session.commit()

    def get_value(self):
        if self.type == Parameter.DataType.BOOLEAN:
            if self.value == "False":
                return False
            else:
                return True

        if self.type == Parameter.DataType.NUMBER:
            return int(self.value)

        if self.type == Parameter.DataType.DATE:
            return datetime.datetime.strptime(self.value, "%H:%M")

        return self.value

    def __repr__(self):
        return '<Parameter %r>' % self.name


#################
# system log
#################

class UserActionLog(db.Model, IdMixin):
    __tablename__ = 'log_useraction'
    userid = db.Column(db.String(64))
    level = db.Column(db.String(20), default="DEBUG") #DEBUG/INFO/ERROR
    message = db.Column(db.String(1024))
    created_at = db.Column(db.DateTime, default=datetime.datetime.now)


class SystemRunningLog(db.Model, IdMixin):
    __tablename__ = 'log_systemrunning'
    level = db.Column(db.String(20), default="INFO") #DEBUG/INFO/ERROR
    message = db.Column(db.String(1024))
    created_at = db.Column(db.DateTime, default=datetime.datetime.now)


#################
# system log
#################

class FtpServer(db.Model, IdMixin, TimestampMixin):
    __tablename__ = 'ftp_servers'
    ip = db.Column(db.String(20))
    port = db.Column(db.Integer)
    name = db.Column(db.String(64))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    ftp_accounts = db.relationship('FtpAccount', backref='ftp', lazy='dynamic')

    def __repr__(self):
        return '<Ftp Server %r>' % self.name


class FtpAccount(db.Model, IdMixin, TimestampMixin):
    __tablename__ = 'ftp_accounts'
    ftp_server_id = db.Column(db.Integer, db.ForeignKey('ftp_servers.id'))
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'))
    username = db.Column(db.String(64))
    password = db.Column(db.String(64))

    def __repr__(self):
        return '<Ftp Account %r>' % self.username


class SambaServer(db.Model, IdMixin, TimestampMixin):
    __tablename__ = 'samba_servers'
    ip = db.Column(db.String(20))
    name = db.Column(db.String(64))
    administrator = db.Column(db.String(64))
    password = db.Column(db.String(64))
    samba_accounts = db.relationship('SambaAccount', backref='samba', lazy='dynamic')

    def __repr__(self):
        return '<Samba Server %r>' % self.name


class SambaAccount(db.Model, IdMixin, TimestampMixin):
    __tablename__ = 'samba_accounts'
    samba_server_id = db.Column(db.Integer, db.ForeignKey('samba_servers.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    password = db.Column(db.String(64))
    quota = db.Column(db.String(64))

    def __repr__(self):
        return '<Samba Account %r>' % self.user_id


class TerminalState(object):
    APPROVED = 'APPROVED'
    WAITING = 'WAITING'
    REJECTED = 'REJECTED'

    @staticmethod
    def get_state_chs(terminal_state):
        state_dict = {
            TerminalState.APPROVED: "自动审批",
            TerminalState.WAITING: "手工审批",
            TerminalState.REJECTED: "拒绝申请"
        }
        return state_dict.get(terminal_state, terminal_state)


class Terminal(db.Model, IdMixin, TimestampMixin):
    __tablename__ = 'terminals'

    mac_address = db.Column(db.String(64), nullable=False)
    seat_number = db.Column(db.String(64), nullable=False)
    description = db.Column(db.String(1024), default="")
    # info = db.Column(db.String(1024), default="{}")
    state = db.Column(db.String(64), default='', index=True)

    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'))
    user = relationship("User", back_populates="terminal")
    place_id = db.Column(db.Integer, db.ForeignKey('places.id'))


class License(db.Model, IdMixin, TimestampMixin):
    __tablename__ = 'licenses'
    system_serial_number = db.Column(db.String(64), default="")
    server_url = db.Column(db.String(64), default="")
    expired_time = db.Column(db.DateTime, default=datetime.datetime.now())
    mac_address = db.Column(db.String(64), default="")
    server_serial_number = db.Column(db.String(64), default="")
    max_desktops = db.Column(db.Integer, default=0)
    max_images = db.Column(db.Integer, default=0)
    max_user = db.Column(db.Integer, default=0)
    max_vcpu = db.Column(db.Integer, default=0)
    max_vmem = db.Column(db.Integer, default=0)
    max_vdisk = db.Column(db.Integer, default=0)


    @staticmethod
    def insert_default_license():
        license = License()
        db.session.add(license)
        db.session.commit()

    def __repr__(self):
        return '<License %r>' % self.id

class HostInfo(db.Model, IdMixin, TimestampMixin):
    __tablename__ = 'hostinfo'
    host_name = db.Column(db.String(64), default="")
    host_ip = db.Column(db.String(64), default="")
    cpu_arch = db.Column(db.String(64), default="x86_64")
    cpu_cores = db.Column(db.Integer, default=0)
    mem = db.Column(db.Integer, default=0)
    mem_used = db.Column(db.Integer, default=0)
    disk = db.Column(db.Integer, default=0)
    disk_used = db.Column(db.Integer, default=0)
    vms = db.Column(db.Integer, default=0)
    running_vms  =db.Column(db.Integer, default=0)
    zone = db.Column(db.String(64), default="nova")
    external_network_state = db.Column(db.String(64), default="down")
    management_network_state =  db.Column(db.String(64), default="down")
    service_state = db.Column(db.String(64), default="down")
    host_status = db.Column(db.String(64), default="down")
    service_status = db.Column(db.String(64), default="enabled")
    #用于指示后台服务能否自动撤离故障主机的虚拟机
    #当该故障主机被处理后将该其置位为False，避免重复处理创建撤离任务
    #当用户手动处理完故障后需手动将该标志位置为True，重新加入自动撤离
    auto_evacuation = db.Column(db.Boolean, default=True)

class Policy(db.Model, IdMixin, TimestampMixin):
    """
    # this is the class which defines the vm access policy, such as usb access policy, clip board policy
    """
    __tablename__ = 'policies'

    name = db.Column(db.String(64), unique=True, index=True, default="default")
    enable_usb = db.Column(db.Boolean, default=True)
    enable_clipboard = db.Column(db.Boolean, default=True)
    enable_audio = db.Column(db.Boolean, default=True)

    courses = db.relationship("Course", backref='policy', lazy='dynamic')

    def __repr__(self):
        return '<Policy %r>' % self.name

    @staticmethod
    def insert_default_policy():
        policy = {
            'default': {
                'enable_usb': True,
                'enable_clipboard': True,
                'enable_audio': True
            }
        }
        for r in policy:
            pol = Policy.query.filter_by(name=r).first()
            if pol is None:
                pol = Policy(name=r)
            pol.enable_usb = policy[r]['enable_usb']
            pol.enable_clipboard = policy[r]['enable_clipboard']
            pol.enable_audio = policy[r]['enable_audio']
            db.session.add(pol)
        db.session.commit()


