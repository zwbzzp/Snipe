# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# terminal api
#
# 20160407 lipeizhao: Create module.

import logging

from flask import jsonify, request, g
from sqlalchemy import and_

from .. import db, csrf
from ..models import Terminal, TerminalState, Place, User, Role, Parameter
from ..terminal.forms import TerminalForm
from .decorators import permission_required
from . import api
from . import utils

LOG = logging.getLogger(__name__)


@api.route('/places', methods=['GET'])
def places():
    # TODO: get places here
    places = Place.query.all()
    place_list = []
    for place in places:
        place_list.append(place.to_json())

    return jsonify({
        'status': 'success',
        'data': {
            'place_list': place_list
        }
    })


@api.route('/terminals/<string:mac_address>', methods=['GET'])
def terminal_detail(mac_address):
    terminal = Terminal.query.\
        filter(Terminal.mac_address == mac_address).first()
    if terminal:
        parameter = Parameter.query.\
                filter(Parameter.name == 'terminal_register_mode').first()
        return jsonify({
            'status': 'success',
            'data': {'place': terminal.place.name,
                     'seat_number': terminal.seat_number,
                     'mac_address': terminal.mac_address,
                     'state': terminal.state,
                     'register_mode': parameter.value if parameter else None}
        })
    return jsonify({
        'status': 'fail',
        'data': 'terminal not exist'
    })

@csrf.exempt
@api.route('/terminals/registration', methods=['POST'])
def terminal_register():
    user = g.current_user

    info = request.json
    place = info['place']
    seat_number = info['seat_number']
    mac_address = info['mac_address']
    mode = info.get('mode', None)

    # check if terminal already existed
    terminal = Terminal.query.\
        filter(Terminal.mac_address == mac_address).first()
    if terminal:
        return jsonify({
            'status': 'fail',
            'data': 'terminal existed'
        })

    place = Place.query.filter(Place.name == place).first()

    # check if place and seat number already existed
    username = place.name + '_' + seat_number
    exist_user = User.query.filter(User.username == username).first()
    if exist_user:
        return jsonify({
            'status': 'fail',
            'data': 'place and seat number existed'
        })

    form = TerminalForm()
    form.place_id.data = place.id if place else None
    form.seat_number.data = seat_number
    form.mac_address.data = mac_address
    form.description.data = \
        place.name if place else '' + '_' + seat_number + '_' + mac_address

    # FIXME: disable csrf token check on this form
    if not form.validate_on_submit() and len(form.errors) == 1:
        terminal = Terminal()
        terminal.place = place
        terminal.seat_number = seat_number
        terminal.mac_address = mac_address
        terminal.description = place.name + '_' + seat_number + '_' + mac_address

        if user.is_administrator() and mode == 'auth':
            # client side approve directly
            # need auth parameter and admin username password
            terminal.state = TerminalState.APPROVED
        else:
            # set terminal state according to system settings
            parameter = Parameter.query.\
                filter(Parameter.name == 'terminal_register_mode').first()
            terminal.state = parameter.value if parameter else TerminalState.WAITING
        db.session.add(terminal)

        role = Role.query.filter(Role.name == 'Terminal').first()
        user = User()
        user.username = place.name + '_' + seat_number
        user.fullname = place.name + '_' + seat_number
        user.password = mac_address
        user.is_device = True
        user.confirmed = True if terminal.state == TerminalState.APPROVED else False
        user.role = role
        db.session.add(user)
        db.session.commit()

        terminal.user = user
        db.session.add(terminal)
        db.session.commit()

        # add new created terminal user to the created courses that related to the place
        courses = place.courses
        for course in courses:
            course.users.append(user)
        db.session.commit()

        LOG.info('Terminal %s created. Alone with user %s created' %
                 ("{0}_{1}".format(terminal.place.name, terminal.seat_number),
                  user.username))
        return jsonify({
            'status': 'success',
            'data': {
                'terminal_state': terminal.state
            }
        })
    else:
        return jsonify({
            'status': 'fail',
            'data': {'errors': form.errors}
        })

