# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# for api user authentication
#
# 20160407 lipeizhao: Create module.


import logging
import datetime
from flask import g, jsonify, request
from flask.ext.httpauth import HTTPBasicAuth
from ...models import User, AnonymousUser
from . import api
# from .utils import is_unauth_endpoint
from .errors import unauthorized, forbidden

auth = HTTPBasicAuth()

LOG = logging.getLogger(__name__)

@auth.verify_password
def verify_password(username_or_token, password):
    # Anonymous user
    if username_or_token == '':
        g.current_user = AnonymousUser()
        return True

    # Token provided
    if password == '':
        g.current_user = User.verify_auth_token(username_or_token)
        g.token_used = True
        return g.current_user is not None

    # User name and password provided
    user = User.query.filter_by(username=username_or_token).first()
    if not user or not user.confirmed:
        return False
    g.current_user = user
    g.token_used = False
    return user.verify_password(password)


@auth.error_handler
def auth_error():
    return unauthorized('Invalid credentials')


@api.before_request
@auth.login_required
def before_request():
    pass
    # if not g.current_user.is_anonymous and \
    #         not g.current_user.confirmed:
    #     return forbidden('Unconfirmed account')


@api.route('/token')
def get_token():
    if getattr(g, "token_used", None):
        return unauthorized('Invalid credentials')

    if isinstance(g.current_user, AnonymousUser):
        return unauthorized('Invalid user')

    time_now = datetime.datetime.now()
    expiration = 7200
    return jsonify({
        'status': 'success',
        'data': {
            'token' : {
                'id': g.current_user.generate_auth_token(expiration=expiration),
                'issued_at': time_now.isoformat(),
                'expires': (time_now + datetime.timedelta(seconds=expiration)).isoformat()
            }
        }
    })
