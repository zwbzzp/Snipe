# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# desktop api
#
# 20160407 lipeizhao: Create module.

import logging

from flask import jsonify, request, g

from .. import db
from ..models import Desktop, SambaAccount, FtpAccount, DesktopState, DesktopType, Policy
from .decorators import permission_required
from . import api
from . import utils
from ..common import password_utils
from phoenix.cloud import compute
from ..desktop.utils import reboot_vm, resume_vm, stop_vm, delete_vm

LOG = logging.getLogger(__name__)


@api.route('/users/me/desktops')
def get_user_desktops():
    if g.current_user:
        desktop_list = []

        # get course desktop for user
        user = g.current_user
        courses = user.courses
        for course in courses:
            desktop = Desktop.query.filter(Desktop.owner == user,
                                           Desktop.course == course).first()
            # if found no course desktop of user, try to assign one from active course desktops
            if not desktop:
                desktop = Desktop.query.with_for_update().filter(Desktop.owner == None,
                                                                 Desktop.desktop_state == DesktopState.ACTIVE,
                                                                 Desktop.course == course).first()
                if desktop:
                    desktop.owner = user
                    db.session.add(desktop)
                    db.session.commit()

                    # set meta data for desktop regarding ftp and samba
                    desktop_metadata = {}
                    ftp_account_list = FtpAccount.query.filter(FtpAccount.course_id == course.id).all()
                    if len(ftp_account_list) > 0:
                        for ftp_account in ftp_account_list:
                            password = str(password_utils.decrypt(ftp_account.password))
                            desktop_metadata["ftp_" + str(ftp_account.ftp_server_id)] = \
                                "IP:" + str(ftp_account.ftp.ip) + \
                                ":Port:" + str(ftp_account.ftp.port) + \
                                ":Username:" + str(ftp_account.username) + \
                                ":Password:" + password

                    samba_account_list = SambaAccount.query.filter(SambaAccount.user_id == user.id).all()
                    if len(samba_account_list) > 0:
                        for samba_account in samba_account_list:
                            desktop_metadata["samba_" + str(samba_account.samba_server_id)] = \
                                "IP:" + str(samba_account.samba.ip) + \
                                ":Username:" + str(samba_account.user_id) + \
                                ":Password:" + str(password_utils.decrypt(samba_account.password))

                    compute.set_meta(server=desktop.vm_ref,
                                     metadata=desktop_metadata)
                    LOG.info('Allocated desktop %s to user %s' % (desktop.name, user.username))

            # get course policy
            desktop_policy = course.policy

            policy = None
            if desktop_policy:
                policy = {
                    'enable_usb': desktop_policy.enable_usb,
                    'enable_clipboard': desktop_policy.enable_clipboard,
                    'enable_audio': desktop_policy.enable_audio
                }

            json_desktop = utils.desktop_to_json(desktop, course.protocol, policy)
            if json_desktop:
                desktop_list.append(json_desktop)

        # get static desktop for user
        desktops = Desktop.query.filter(Desktop.owner == user,
                                        Desktop.desktop_type == DesktopType.STATIC,
                                        Desktop.desktop_state == DesktopState.ACTIVE).all()
        if desktops:
            desktop_metadata = {}
            samba_account_list = SambaAccount.query.filter(SambaAccount.user_id == user.id).all()
            if len(samba_account_list) > 0:
                for samba_account in samba_account_list:
                    desktop_metadata["samba_" + str(samba_account.samba_server_id)] = \
                        "IP:" + str(samba_account.samba.ip) + \
                        ":Username:" + str(samba_account.user_id) + \
                        ":Password:" + str(password_utils.decrypt(samba_account.password))

            # get default policy
            desktop_policy = Policy.query.filter(Policy.name == 'default').first()
            policy = {
                'enable_usb': desktop_policy.enable_usb,
                'enable_clipboard': desktop_policy.enable_clipboard,
                'enable_audio': desktop_policy.enable_audio
            }

            for desktop in desktops:
                compute.set_meta(server=desktop.vm_ref,
                                 metadata=desktop_metadata)
                json_desktop = utils.desktop_to_json(desktop, policy=policy)
                if json_desktop:
                    desktop_list.append(json_desktop)
                    LOG.info('Allocated desktop %s to user %s' % (desktop.name, user.username))

        return jsonify({
            'status': 'success',
            'data': {
                'desktop_list': desktop_list,
                'gateway_list': [],
                'lock_info': 'unlock'
            }
        })


@api.route('/desktops/<string:id>/action', methods=['POST'])
def operate_vm(id):
    user = g.current_user
    action, param = request.json.popitem()

    desktop = user.get_desktop(int(id))
    if not desktop:
        LOG.info('user %s did not own desktop %s' % (user.username, desktop.name))
        return jsonify({
            'status': 'fail',
            'data': 'user %s did not own desktop %s' % (user.username, desktop.name)
        })

    # TODO: should judge if the user has permission to operate on the vm. object granurity?
    if action == 'resume':
        resume_vm(desktop.vm_ref)
    elif action == 'reboot':
        reboot_vm(desktop.vm_ref)
    elif action == 'shutdown':
        stop_vm(desktop.vm_ref)
    else:
        return jsonify({
            'status': 'fail',
            'data': 'action %s not support' % action
        })
    LOG.info('user %s %s desktop %s success' % (user.username, action, desktop.name))
    return jsonify({
        'status': 'success',
        'data': None
    })
