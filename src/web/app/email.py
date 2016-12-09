# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# Mail
#
# 2016/2/22 fengyc : Init

from flask import current_app, render_template
from flask.ext.mail import Message
from . import mail
#from .celery_tasks import send_mail as celery_send_mail


def send_async_email(app, msg):
    with app.app_context():
        mail.send(msg)


def send_email(to, subject, template, **kwargs):
    try:
        app = current_app._get_current_object()
        msg = Message(app.config['FLASKY_MAIL_SUBJECT_PREFIX']+' '+subject,
                      sender=app.config['FLASKY_MAIL_SENDER'], recipients=[to])
        msg.body = render_template(template+'.txt', **kwargs)
        msg.html = render_template(template+'.html', **kwargs)
        #celery_send_mail.delay(msg)
        mail.send(msg)
    except Exception as e:
        raise

