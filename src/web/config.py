# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# Flask config
#
# All configuration items that could not be change in runtime, should be placed
# here. Otherwise, they should be stored in database and updated by the
# administrators in runtime.
#
# 2016/2/16 fengyc : Init

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

    # oslo.config
    OSLO_CONFIG = from_env('OSLO_CONFIG') or \
        os.path.join(basedir, '../etc/phoenix.ini')

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

    # celery
    CELERY_BROKER_URL = from_env('CELERY_BROKER_URL')
    CELERY_RESULT_BACKEND = from_env('CELERY_RESULT_BACKEND')
    CELERY_IMPORTS = ('app.celery_tasks',)
    CELERY_TASK_SERIALIZER = 'pickle'
    CELERY_ACCEPT_CONTENT = ['pickle', 'json']
    CELERY_RESULT_SERIALIZER = 'pickle'
    CELERYD_HIJACK_ROOT_LOGGER = False

    # mail
    MAIL_SERVER = from_env('MAIL_SERVER')
    MAIL_PORT = from_env_int('MAIL_PORT')
    MAIL_USE_SSL = from_env_bool('MAIL_USE_SSL')
    MAIL_USE_TLS = from_env_bool('MAIL_USE_TLS')
    MAIL_USERNAME = from_env('MAIL_USERNAME')
    MAIL_PASSWORD = from_env('MAIL_PASSWORD')

    # admin mail
    FLASKY_MAIL_SUBJECT_PREFIX = '[Flasky]'
    FLASKY_MAIL_SENDER = from_env('FLASKY_MAIL_SENDER') or MAIL_USERNAME
    FLASKY_ADMIN = from_env('FLASKY_ADMIN')

    # ganglia
    GANGLIA_URL = from_env('GANGLIA_URL')

    # wtf and csrf
    WTF_CSRF_ENABLED = True
    WTF_CSRF_METHODS = ['PUT', 'POST', 'PATCH', 'DELETE']

    # i18n
    LANGUAGES = {
        'en': 'English',
        'zh': 'Chinese',
    }

    @classmethod
    def init_app(cls, app):
        pass


class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_ECHO = True
    SQLALCHEMY_DATABASE_URI = from_env('SQLALCHEMY_DATABASE_URI') or \
         'sqlite:///' + os.path.join(basedir, 'data-dev.sqlite')
    CELERY_RESULT_BACKEND = from_env('CELERY_RESULT_BACKEND') or \
        'db+sqlite:///' + os.path.join(basedir, 'celery-dev.sqlite')
    CELERY_ALWAYS_EAGER = False     # enable this to debug celery task


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = from_env('SQLALCHEMY_DATABASE_URI') or \
        'sqlite:///' + os.path.join(basedir, 'data-test.sqlite')
    CELERY_RESULT_BACKEND = from_env('CELERY_RESULT_BACKEND') or \
        'db+sqlite:///' + os.path.join(basedir, 'celery-test.sqlite')
    PRESERVE_CONTEXT_ON_EXCEPTION = True


class ProductConfig(Config):
    SQLALCHEMY_DATABASE_URI = from_env('SQLALCHEMY_DATABASE_URI') or \
         'sqlite:///' + os.path.join(basedir, 'data.sqlite')
    CELERY_RESULT_BACKEND = from_env('CELERY_RESULT_BACKEND') or \
        'db+sqlite:///' + os.path.join(basedir, 'celery.sqlite')
    SSL_DISABLE = from_env_bool('SSL_DISABLE', False)

    @classmethod
    def init_app(cls, app):
        Config.init_app(app)

        # import logging
        # from logging.handlers import TimedRotatingFileHandler
        # log_file = from_env('LOG_FILE', 'app.log')
        # log_level = from_env('LOG_LEVEL', 'INFO')
        # log_reserved = from_env_int('LOG_RESERVED', 5)
        # trf_handler = TimedRotatingFileHandler(log_file, when='midnight',
        #                                        backupCount=log_reserved)
        # trf_handler.setLevel(logging._nameToLevel[log_level])
        # app.logger.addHandler(trf_handler)


config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'product': ProductConfig,

    'default': DevelopmentConfig,
}
