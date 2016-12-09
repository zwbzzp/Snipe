# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# App
#
# 2016/2/16 fengyc : Init

import os
import sys
import logging
import logging.config
from inspect import getmembers, isfunction
from flask import Flask
from flask.ext.bootstrap import Bootstrap
from flask.ext.login import LoginManager
from flask.ext.moment import Moment
from flask.ext.babel import Babel
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.mail import Mail
from flask.ext.wtf import CsrfProtect
from flask.ext.principal import Principal
from celery import Celery, current_app as current_celery
from config import config
from . import jinja_filters

if __name__.find('.') > 0:
    flask_name = __name__.split('.')[0]
else:
    flask_name = __name__


class HackedSQLAlchemy(SQLAlchemy):
    """A simple hack to support isolation level"""

    def apply_driver_hacks(self, app, info, options):
        if app.config.get('SQLALCHEMY_ISOLATION_LEVEL'):
            options['isolation_level'] = app.config['SQLALCHEMY_ISOLATION_LEVEL']
        elif info.drivername.startswith('mysql'):
            options['isolation_level'] = 'READ COMMITTED'
        elif info.drivername == 'sqlite':
            options['isolation_level'] = 'READ UNCOMMITTED'
        super(HackedSQLAlchemy, self).apply_driver_hacks(app, info, options)


app = Flask(flask_name)
bootstrap = Bootstrap()
moment = Moment()
babel = Babel()
db = HackedSQLAlchemy()
mail = Mail()
csrf = CsrfProtect()


login_manager = LoginManager()
login_manager.session_protection = 'strong'
login_manager.login_view = 'auth.login'
login_manager.login_message = ''


def create_app(config_name):
    # app = Flask(__name__)
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)

    # init extensions
    # TODO: we could load config from database now, update the settings
    db.init_app(app)

    # fix osls.config
    try:
        import phoenix.config as cfg
        cfg.CONF([app.config['OSLO_CONFIG']])
    except:
        pass

    # init logging
    logging.config.fileConfig(app.config['LOG_CONFIG'])

    bootstrap.init_app(app)
    moment.init_app(app)
    babel.init_app(app)
    mail.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    Principal(app)

    # init custom jinja filters
    custom_filters = {
        name: function for name, function in getmembers(jinja_filters) if isfunction(function)
        }
    app.jinja_env.filters.update(custom_filters)

    # enable ssl
    if not app.debug and not app.testing and not app.config['SSL_DISABLE']:
        from flask.ext.sslify import SSLify
        sslify = SSLify(app)

    # register blueprints
    from .main import main as main_blueprint
    app.register_blueprint(main_blueprint)

    from .auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint, url_prefix='/auth')

    from .account import account as account_blueprint
    app.register_blueprint(account_blueprint, url_prefix='/account')

    from .teachers.account import account as account_blueprint
    app.register_blueprint(account_blueprint, url_prefix='/teachers/account')

    from .students.account import account as account_blueprint
    app.register_blueprint(account_blueprint, url_prefix='/students/account')

    from .edu import edu as edu_blueprint
    app.register_blueprint(edu_blueprint, url_prefix='/edu')

    from .teachers.edu import edu as edu_blueprint
    app.register_blueprint(edu_blueprint, url_prefix='/teachers/edu')

    from .students.edu import edu as edu_blueprint
    app.register_blueprint(edu_blueprint, url_prefix='/students/edu')

    from .schedule import schedule as schedule_blueprint
    app.register_blueprint(schedule_blueprint, url_prefix='/schedule')

    from .setting import setting as setting_blueprint
    app.register_blueprint(setting_blueprint, url_prefix='/setting')

    from .image import image as image_blueprint
    app.register_blueprint(image_blueprint, url_prefix='/image')

    from .teachers.image import image as image_blueprint
    app.register_blueprint(image_blueprint, url_prefix='/teachers/image')

    from .desktop import desktop as desktop_blueprint
    app.register_blueprint(desktop_blueprint, url_prefix='/desktop')

    from .teachers.desktop import desktop as desktop_blueprint
    app.register_blueprint(desktop_blueprint, url_prefix='/teachers/desktop')

    from .students.desktop import desktop as desktop_blueprint
    app.register_blueprint(desktop_blueprint, url_prefix='/students/desktop')

    from .api_2_0 import api as api_1_0_blueprint
    app.register_blueprint(api_1_0_blueprint, url_prefix='/api/v1.0')

    from .teachers.api_2_0 import api as api_1_0_blueprint
    app.register_blueprint(api_1_0_blueprint, url_prefix='/teachers/api/v1.0')

    from .students.api_2_0 import api as api_1_0_blueprint
    app.register_blueprint(api_1_0_blueprint, url_prefix='/students/api/v1.0')

    from .log import log as log_blueprint
    app.register_blueprint(log_blueprint, url_prefix='/log')

    from .teachers.log import log as log_blueprint
    app.register_blueprint(log_blueprint, url_prefix='/teachers/log')

    from .students.log import log as log_blueprint
    app.register_blueprint(log_blueprint, url_prefix='/students/log')

    from .storage import storage as storage_blueprint
    app.register_blueprint(storage_blueprint, url_prefix='/storage')

    from .teachers.storage import storage as storage_blueprint
    app.register_blueprint(storage_blueprint, url_prefix='/teachers/storage')

    from .terminal import terminal as terminal_blueprint
    app.register_blueprint(terminal_blueprint, url_prefix='/terminal')

    from .monitor import monitor as monitor_blueprint
    app.register_blueprint(monitor_blueprint, url_prefix='/monitor')

    from .network import network as network_blueprint
    app.register_blueprint(network_blueprint, url_prefix='/network')

    from .vmotion import vmotion as vmotion_blueprint
    if vmotion_blueprint:
        app.register_blueprint(vmotion_blueprint, url_prefix='/vmotion')

    return app


# Global flask app and celery app (shared in a process, not across processes)
# IMPORTANT: THIS IS VERY IMPORTANT IN FLASK CELERY INTEGRATION.

app = create_app(os.environ.get('FLASK_CONFIG') or 'default')
