# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# error handlers: include 400, 401, 403, 500 error code
#
# 20160407 lipeizhao: Create module.

import logging
from flask import jsonify
from .exceptions import ValidationError
from . import api

LOG = logging.getLogger(__name__)


def bad_request(message):
    response = jsonify({'status': 'error',
                        'message': 'bad request',
                        'data': message})
    response.status_code = 400
    return response


def unauthorized(message):
    response = jsonify({'status': 'error',
                        'message': 'unauthorized',
                        'data': message})
    response.status_code = 401
    return response


def forbidden(message):
    response = jsonify({'status': 'error',
                        'message': 'forbidden',
                        'data': message})
    response.status_code = 403
    return response


def general_exception(message):
    response = jsonify({'status': 'error',
                        'message': 'exception raised',
                        'data': message})
    response.status_code = 500
    return response


@api.errorhandler(ValidationError)
def validation_error(e):
    return bad_request(e.args[0])


# for general exception handle
@api.errorhandler(Exception)
def general_exception_error(e):
    LOG.exception('exception raised')
    return general_exception(e.args[0])
