# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# comment
#
# 16-7-9 qinjinghui : Init


import os
from werkzeug.security import generate_password_hash as gen_hash

basedir = os.path.abspath((os.path.dirname(__file__)))


def from_env(key, default=None):
    return os.environ.get(key, default=default)


def from_env_int(key, default=0):
    value = from_env(key)
    try:
        return int(value)
    except:
        pass
    return default


def from_env_bool(key, default=False, ignore_case=True):
    true_values = ['True', 'T', 'Yes', 'Y', 'Ok', 'O']
    upper_true_values = [i.upper() for i in true_values]
    value = from_env(key)
    if value is not None and ignore_case:
        return value.upper() in upper_true_values
    else:
        return value in true_values



class Config:
    SECRET_KEY = from_env('SECRET_KEY', gen_hash('TOP_SECRET'))
    MAX_CONTENT_LENGTH = from_env_int('MAX_CONTENT_LENGTH', 10485760)

    # log config
    LOG_CONFIG = from_env('LOG_CONFIG') or \
        os.path.join(basedir, 'logging.ini')

    # bootstrap
    BOOTSTRAP_SERVE_LOCAL = from_env_bool('BOOTSTRAP_SERVE_LOCAL')
    BOOTSTRAP_QUERYSTRING_REVVING = from_env_bool('BOOTSTRAP_QUERYSTRING_REVVING')
    BOOTSTRAP_LOCAL_SUBDOMAIN = from_env('BOOTSTRAP_LOCAL_SUBDOMAIN', '')

    # sqlalchemy
    SQLALCHEMY_COMMIT_ON_TEARDOWN = True
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_DATABASE_URI = from_env('SQLALCHEMY_DATABASE_URI')

    # mail
    MAIL_SERVER = from_env('MAIL_SERVER')
    MAIL_PORT = from_env_int('MAIL_PORT')
    MAIL_USE_SSL = from_env_bool('MAIL_USE_SSL')
    MAIL_USE_TLS = from_env_bool('MAIL_USE_TLS')
    MAIL_USERNAME = from_env('MAIL_USERNAME')
    MAIL_PASSWORD = from_env('MAIL_PASSWORD')

    FLASKY_MAIL_SUBJECT_PREFIX = '[Flasky]'
    FLASKY_MAIL_SENDER = from_env('FLASKY_MAIL_SENDER') or MAIL_USERNAME
    FLASKY_ADMIN = os.environ.get('FLASKY_ADMIN')

    # i18n
    LANGUAGES = {
        'en': 'English',
        'zh': 'Chinese',
    }

    @staticmethod
    def init_app(app):
        pass


class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_ECHO = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('SQLALCHEMY_DATABASE_URI') or \
        'sqlite:///' + os.path.join(basedir, 'data-dev.sqlite')


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('SQLALCHEMY_DATABASE_URI') or \
        'sqlite:///' + os.path.join(basedir, 'data-test.sqlite')
    PRESERVE_CONTEXT_ON_EXCEPTION = True


class ProductionConfig(Config):
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'data.sqlite')
    SSL_DISABLE = from_env_bool('SSL_DISABLE', False)

    @classmethod
    def init_app(cls, app):
        Config.init_app(app)


config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,

    'default': DevelopmentConfig
}