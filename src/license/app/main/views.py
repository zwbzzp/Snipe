# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# comment
#
# 16-7-9 qinjinghui : Init


from flask import render_template, session, redirect, url_for, current_app
from flask.ext.login import login_required,current_user
from .. import db
from ..models import User
from ..email import send_email
from . import main
from .forms import NameForm



@main.route('/', methods=['GET', 'POST'])
@login_required
def index():
    form = NameForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.name.data).first()
        if user is None:
            user = User(username=form.name.data)
            db.session.add(user)
            session['known'] = False
            if current_app.config['FLASKY_ADMIN']:
                send_email(current_app.config['FLASKY_ADMIN'], 'New User',
                           'mail/new_user', user=user)
        else:
            session['known'] = True
        session['name'] = form.name.data
        return redirect(url_for('.index'))
    if current_user.is_administrator():
        return redirect(url_for('account.users'))
    else:
        return redirect(url_for('instance.instances'))
    # return render_template('index.html',
    #                        form=form, name=session.get('name'),
    #                        known=session.get('known', False))
