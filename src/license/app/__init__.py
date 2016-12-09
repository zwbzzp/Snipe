# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# comment
#
# 16-7-9 qinjinghui : Init

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
from config import config
#from . import jinja_filters

if __name__.find('.') > 0:
    flask_name = __name__.split('.')[0]
else:
    flask_name = __name__


app = Flask(flask_name)
bootstrap = Bootstrap()
moment = Moment()
babel = Babel()
db = SQLAlchemy()
mail = Mail()
csrf = CsrfProtect()

login_manager = LoginManager()
login_manager.session_protection = 'strong'
login_manager.login_view = 'account.login'
login_manager.login_message = ''


def create_app(config_name):

    app.config.from_object(config[config_name])
    config[config_name].init_app(app)

    # init extensions
    # TODO: we could load config from database now, update the settings
    db.init_app(app)

    # init logging
    logging.config.fileConfig(app.config['LOG_CONFIG'])

    bootstrap.init_app(app)
    moment.init_app(app)
    babel.init_app(app)
    mail.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    Principal(app)

    # enable ssl
    if not app.debug and not app.testing and not app.config['SSL_DISABLE']:
        from flask.ext.sslify import SSLify
        sslify = SSLify(app)

    # register blueprints
    from .main import main as main_blueprint
    app.register_blueprint(main_blueprint)

    from .account import account as account_blueprint
    app.register_blueprint(account_blueprint, url_prefix='/account')

    from .instance import instance as instance_blueprint
    app.register_blueprint(instance_blueprint, url_prefix='/instance')

    return app

app = create_app(os.environ.get('FLASK_CONFIG') or 'default')