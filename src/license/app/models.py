# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# comment
#
# 16-7-9 qinjinghui : Init


import datetime

from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from flask import current_app
from flask.ext.login import UserMixin, AnonymousUserMixin
from flask.ext.sqlalchemy import BaseQuery
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy import case
from sqlalchemy.orm import relationship

from . import login_manager
from . import db
from.randompsw import get_random_password

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


##################
# auth
##################
class Permission:
    USER = 0x02
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
            'User': {
                'permissions': (Permission.USER),
                'description': 'user role'
            },
            'Bot': {
                'permissions': (Permission.USER),
                'description': 'bot role'
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

class User(UserMixin,TimestampMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, index=True)
    email = db.Column(db.String(64), unique=True, index=True)
    phone = db.Column(db.String(11))
    organization = db.Column(db.String(64), index=True)
    os_auth_url = db.Column(db.String(64))
    is_active = db.Column(db.Boolean, default=True)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))
    origin_password = db.Column(db.String(128))
    password_hash = db.Column(db.String(128), default="")
    confirmed = db.Column(db.Boolean, default=False)

    instances = db.relationship('Instance', backref='user', lazy='dynamic')
    # instances = db.relationship('Instance', cascade = 'all,delete-orphan',
    #                             single_parent = True, backref = db.backref('user', cascade='all'), lazy='dynamic')


    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        if self.password_hash == "":
            return self.origin_password == password
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

    @staticmethod
    def verify_auth_token(token):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except:
            return None
        return User.query.get(data['id'])

    @staticmethod
    def insert_default_users():
        users = {
            'admin': {
                'email': 'admin@example.com',
                'password': 'admin123',
                'organization': 'vinzor',
                'role': 'Administrator',
            },
            'sysu': {
                'email': 'sysu@example.com',
                'password': get_random_password(),
                'organization': "sysu",
                'role': 'User',
            },
            'anonymousrobot':{
                'email': "anonymousrobot@gmail.com",
                'password':'dacvrwomby',
                'organization': 'vinzor',
                'role': 'Bot',
            }
        }
        for u in users:
            user = User.query.filter_by(username=u).first()
            if user is None:
                user = User(username=u, email=users[u]['email'], organization=users[u]['organization'], is_active=True, confirmed=True)
                user.password = users[u]['password']
                user.origin_password = users[u]['password']
                if 'role' in users[u]:
                    user.role = Role.query.filter_by(name=users[u]['role']).first()
            db.session.add(user)
        db.session.commit()

    def __repr__(self):
        return '<User %r>' % self.username


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
# Instance
##################

class InstanceStatus(object):
    TOUPLOAD = 'TOUPLOAD'
    INFOERROR = 'INFOERROR'
    TODOWNLOAD = 'TODOWNLOAD'
    DOWNLOADERROR = 'DOWNLOADERROR'
    EXPIRED = 'EXPIRED'

    @staticmethod
    def get_type_chs(instance_status):
        type_dict = {InstanceStatus.TOUPLOAD: "未上传主机信息",
                     InstanceStatus.INFOERROR: "主机信息被篡改",
                     InstanceStatus.TODOWNLOAD: "可下载最新 License",
                     InstanceStatus.DOWNLOADERROR: "下载异常",
                     InstanceStatus.EXPIRED: "实例已过期"}
        return type_dict.get(instance_status, instance_status)


class Instance(db.Model, IdMixin, TimestampMixin):
    instancename = db.Column(db.String(64), unique=True, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'))
    max_vm = db.Column(db.Integer, default=0)
    max_image = db.Column(db.Integer, default=0)
    max_user = db.Column(db.Integer, default=0)
    max_vcpu = db.Column(db.Integer, default=0)
    max_vmem = db.Column(db.Integer, default=0)
    max_vdisk = db.Column(db.Integer, default=0)
    status = db.Column(db.String(64), default='TOUPLOAD')
    expired_time = db.Column(db.DateTime, default=datetime.datetime.now)
    mac = db.Column(db.String(256), default='')
    serial_number = db.Column(db.String(256), default='')
    check_code = db.Column(db.Text(), default='')
    public_key = db.Column(db.Text(), default='')
    download = db.Column(db.Integer, default=0)

    def get_status_str(self):
        return InstanceStatus.get_type_chs(self.status)

    def __repr__(self):
        return '<Instance %r>' % self.instancename


