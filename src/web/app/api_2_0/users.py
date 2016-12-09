# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# user api
#
# 20160407 lipeizhao: Create module.

import logging
from flask import g, jsonify, request
from . import api
from .. import db

LOG = logging.getLogger(__name__)


@api.route('/users/me/reset_password', methods=['POST'])
def reset_password():
    user = g.current_user
    password = request.json['password']
    password_repeat = request.json['password_repeat']
    if password == password_repeat:
        user.password = password
        db.session.add(user)
        db.session.commit()
        return jsonify({
            'status' : 'success',
            'data': None
        })
    else:
        return jsonify({
            'status': 'fail',
            'data': {
                'password': 'password and the repeat password not equal'
            }
        })


@api.route('/users/me/is_administrator', methods=['GET'])
def is_administrator():
    user = g.current_user
    if user.is_administrator():
        return jsonify({
            'status' : 'success',
            'data': 'true'
        })
    return jsonify({
        'status' : 'success',
        'data': 'false'
    })