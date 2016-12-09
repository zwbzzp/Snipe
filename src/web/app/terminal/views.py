# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# comment
#
# 2016/6/1 0001 Jay : Init

import json

from flask import render_template, redirect, url_for, flash, \
    request, jsonify, abort

from . import terminal
from .forms import PlaceForm, TerminalForm
from .. import db
from ..models import Place, Terminal, TerminalState, User, Parameter, Role


@terminal.route('/places', methods=['GET', 'POST'])
def places():
    form = PlaceForm()
    if form.validate_on_submit():
        place = Place(name=form.name.data,
                      address=form.address.data)
        db.session.add(place)
        db.session.commit()
        flash("添加课室成功", category='info')
        return redirect(url_for('terminal.places'))
    places = Place.query.all()
    return render_template('terminal/places.html', places=places, form=form)


@terminal.route('/places', methods=['DELETE'])
def delete_places():
    place_id_list = request.json
    result_json = {
        'result': 'success'
    }
    for place_id in place_id_list:
        place = Place.query.get(place_id)
        if place is None:
            flash("课室不存在，删除失败", category="error")
        else:
            course_count = place.courses.count()
            if course_count > 0:
                flash("课室{0}正在被课程占用，删除失败".format(place.name), category="error")
            else:
                db.session.delete(place)
                flash("课室{0}删除成功".format(place.name), category='info')
    db.session.commit()
    return jsonify(result_json)


@terminal.route('/places/<int:place_id>', methods=['PUT'])
def update_place(place_id):
    place = Place.query.get(place_id)
    if not place:
        abort(404)
    form = PlaceForm()
    result_json = {
        'result': 'success'
    }
    if form.validate_on_submit():
        place.name = form.name.data
        place.address = form.address.data
        db.session.add(place)
        db.session.commit()
        flash("修改课室信息成功", category='info')
    else:
        flash("修改失败，课室名称或课室地址不能为空", category="error")
    return jsonify(result_json)


@terminal.route('/registration', methods=['GET', 'POST'])
def registration():
    form = TerminalForm()
    if form.validate_on_submit():
        place = Place.query.get(form.place_id.data)
        if Terminal.query.filter_by(mac_address=form.mac_address.data).first():
            flash("创建终端失败，MAC地址已存在", category="error")
            return redirect(url_for("terminal.registration"))

        parameter = Parameter.query.\
                filter(Parameter.name == 'terminal_register_mode').first()

        terminal_user_name = "{0}_{1}".format(place.name, form.seat_number.data)
        terminal_user_password = form.mac_address.data
        role = Role.query.filter(Role.name == 'Terminal').first()
        user = User()
        user.username = terminal_user_name
        user.fullname = "{0}_{1}".format('terminal', terminal_user_name)
        user.role = role
        user.password = terminal_user_password
        user.is_device = True
        user.confirmed = True if parameter.value == TerminalState.APPROVED else False
        db.session.add(user)
        db.session.flush()

        terminal = Terminal(mac_address=form.mac_address.data,
                            seat_number=form.seat_number.data,
                            description=form.description.data,
                            user_id=user.id,
                            place_id=place.id,
                            state=parameter.value if parameter else TerminalState.WAITING)
        db.session.add(terminal)
        db.session.commit()
        flash('创建终端申请成功', category='info')
        return redirect(url_for("terminal.registration"))
    for field, msg in form.errors.items():
        flash("{0}: {1}".format(field, msg[0]), category="error")
    terminal_list = {}
    terminal_list["approved"] = Terminal.query.filter_by(state=TerminalState.APPROVED).all()
    terminal_list["rejected"] = Terminal.query.filter_by(state=TerminalState.REJECTED).all()
    terminal_list["waiting"] = Terminal.query.filter_by(state=TerminalState.WAITING).all()
    return render_template('terminal/registration.html',
                           form=form, terminal_list=terminal_list)


@terminal.route('/registration', methods=['PUT'])
def update_registration():
    # TODO: 更新已通过审核的终端信息
    abort(405)


@terminal.route('/registration', methods=['DELETE'])
def delete_registration():
    terminal_id_list = request.json
    result_json = {
        'result': 'success'
    }
    for terminal_id in terminal_id_list:
        terminal = Terminal.query.filter_by(id=terminal_id).first()
        user = terminal.user
        if user:
            db.session.delete(terminal)
            db.session.delete(user)
    db.session.commit()
    flash("删除终端成功", category='info')
    return jsonify(result_json)


@terminal.route('/registration/approval', methods=['PUT'])
def approve_registration():
    terminal_id_list = request.json
    result_json = {
        'result': 'success'
    }
    for terminal_id in terminal_id_list:
        terminal = Terminal.query.get(terminal_id)
        if terminal is not None:
            terminal.state = TerminalState.APPROVED
            db.session.add(terminal)

            user = terminal.user
            user.confirmed = True
            db.session.add(user)
    db.session.commit()
    flash("已成功通过审批", category='info')
    return jsonify(result_json)


@terminal.route('/registration/rejection', methods=['PUT'])
def reject_registration():
    terminal_id_list = request.json
    result_json = {
        'result': 'success'
    }
    for terminal_id in terminal_id_list:
        terminal = Terminal.query.get(terminal_id)
        if terminal is not None:
            terminal.state = TerminalState.REJECTED
            db.session.add(terminal)
    db.session.commit()
    flash("已成功拒绝审批", category='info')
    return jsonify(result_json)
