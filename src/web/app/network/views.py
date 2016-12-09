# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# comment
#
# 2016/7/25 chengkang : Init

from flask import render_template, request, jsonify, abort, current_app, redirect, url_for
from flask.ext.login import login_required, current_user
from . import network
from . import utils
from ..models import Desktop
from .. import db
from .forms import AssociateIPForm, AllocateIPForm, SecurityGroupCreateForm, SecurityGroupUpdateForm, \
                SecgroupRuleCreateForm
from ..celery_tasks import sync_openstack
from phoenix.db.models import FloatingIp
from phoenix import db as FloatingIpUtils
from phoenix.cloud import network as OpenstackNetworkService

from ..log.utils import UserActionLogger
import logging

LOG = logging.Logger(__name__)
ua_logger = UserActionLogger()
is_neutron_network = OpenstackNetworkService.is_neutron_network()


@network.route('/floatingips', methods=['GET'])
@login_required
def floatingips():
    last_sync_time = FloatingIpUtils.get_last_sync_time()

    associate_ip_form = AssociateIPForm()
    allocate_ip_form    = AllocateIPForm()
    return render_template("network/floatingip.html", last_sync_time=last_sync_time,
                           associate_ip_form=associate_ip_form,
                           allocate_ip_form=allocate_ip_form)


@network.route('/floatingips/table', methods=['GET', 'POST'])
@login_required
def floatingip_table():
    col_map = {
        "0": "ref_id",
        "1": "ip_address",
        "2": "status",
        "3": "external_network_id"
    }

    sEcho = request.args.get('sEcho', "1")
    iDisplayStart = request.args.get("iDisplayStart", "0")
    iDisplayLength = request.args.get("iDisplayLength", "10")
    sSearch = request.args.get("sSearch", '')
    iSortCol = request.args.get("iSortCol_0", '0')
    sSortDir = request.args.get("sSortDir_0", '')

    sort_col = col_map[iSortCol]
    if sSortDir == "desc":
        sort_col += " desc"

    query = FloatingIpUtils.get_floating_ips(sort_col, sSearch)

    page_index = int(iDisplayStart) // int(iDisplayLength)
    # FIXME: the query is a sqlalchemy query object, not a flask-sqlalchemy
    # basequery object. If we want to paginate it, we can install a
    # sqlalchemy-pagination extension, but here we just do a simple treatment
    # which is enough.
    floatingip_list = query.offset(page_index * int(iDisplayLength)).limit(
        iDisplayLength).all()
    ret_floatingip_list = []
    is_neutron_network = OpenstackNetworkService.is_neutron_network()
    if is_neutron_network:
        external_network_dict = dict([ (network["id"], network["name"]) for \
                network in utils.list_external_networks()])

    nova_floatingips_dict = dict([(str(ip.id), ip.instance_id) for ip in \
        OpenstackNetworkService.list_floatingips()])
    for floatingip in floatingip_list:
        item = {}
        item["ref_id"] = floatingip.ref_id
        item["ip"] = floatingip.ip_address

        vm_ref = nova_floatingips_dict.get(floatingip.ref_id)
        if vm_ref:
            desktop = Desktop.query.filter_by(vm_ref=vm_ref).first()
            # FIXME: if desktop has no name, we should the (vm_ref) as its alias
            alias = ("(" + vm_ref + ")")
            item["desktop"] = (desktop.name or alias) if desktop else alias
        else:
            item["desktop"] = None

        item["pool"] = external_network_dict.get(floatingip.external_network_id, "-") \
            if is_neutron_network else floatingip.external_network_id
        item["operation"] = floatingip.status
        ret_floatingip_list.append(item)

    ret_data = {
        "sEcho": sEcho,
        "iTotalRecords": str(query.count()),
        "iTotalDisplayRecords": str(query.count()),
        "aaData": ret_floatingip_list
    }

    return jsonify(ret_data)


@network.route('/floatingips/sync', methods=['PUT'])
@login_required
def floatingip_sync():
    ret = {'status': '', 'data': ''}
    try:
        sync_openstack.delay()
        ret['status'] = 'success'
        ua_logger.info(current_user, '同步浮动IP')
    except Exception as ex:
        LOG.exception('Sync floating ips fail')
        ret['status'] = 'error'
        ret['message'] = str(ex)
    return jsonify(ret)


@network.route('/floatingips/disassociate', methods=['PUT'])
@login_required
def floatingips_disassociate():
    ret = {'status': 'success', 'data': {"success_list":[], "fail_list": []}}

    fip_ref_ids = request.json
    nova_floatingips_dict = dict([(str(ip.id), ip.instance_id) for ip in \
        OpenstackNetworkService.list_floatingips()])
    for fip_ref_id in fip_ref_ids:
        fip = FloatingIpUtils.get_floating_ip_by_ref_id(fip_ref_id)
        if not fip:
            ret['data']['fail_list'].append({'ref_id': fip_ref_id, 'ip': None, 'reason': '未找到该浮动IP'})
            continue

        vm_ref = nova_floatingips_dict.get(fip.ref_id)
        desktop = Desktop.query.filter_by(vm_ref=vm_ref).first() if vm_ref else None
        success = False
        if is_neutron_network:
            try:
                update_dict = {'port_id': None}
                OpenstackNetworkService.update_floatingip(fip_ref_id, {'floatingip': update_dict})
                ret['data']['success_list'].append({'ref_id': fip.ref_id, 'ip': fip.ip_address})
                success = True
            except Exception as ex:
                LOG.exception('Disassociate floating ip "%s" with instance "%s" fail' % (fip.ip_address, vm_ref))
                ret['data']['fail_list'].append({'ref_id': fip.ref_id, 'ip': fip.ip_address, 'reason': str(ex)})
        else:
            # FIXME: when the floating ip's instance_id is None,
            # we think it's not associated with any instance
            if not vm_ref:
                ret['data']['success_list'].append({'ref_id': fip.ref_id, 'ip': fip.ip_address})
                success = True
            else:
                try:
                    OpenstackNetworkService.remove_floating_ip(vm_ref, fip.ip_address)
                    ret['data']['success_list'].append({'ref_id': fip.ref_id, 'ip': fip.ip_address})
                    success = True
                except Exception as ex:
                    LOG.exception('Disassociate floating ip "%s" with instance "%s" fail' % (fip.ip_address, vm_ref))
                    ret['data']['fail_list'].append({'ref_id': fip.ref_id, 'ip': fip.ip_address, 'reason': str(ex)})

        if success:
            ua_logger.info(current_user, '解除浮动IP"%s"的绑定' % fip.ip_address)
            if desktop:
                desktop.floating_ip = None
                db.session.add(desktop)
                db.session.commit()

            FloatingIpUtils.reclaim_floating_ip(fip.ip_address)

    return jsonify(ret)


@network.route('/floatingips/associate', methods=['PUT'])
@login_required
def floatingip_associate():
    ret = {'status': '', 'data': ''}

    associate_ip_form = AssociateIPForm()
    if associate_ip_form.validate_on_submit():
        fip_ref_id = associate_ip_form.fip_ref_id.data
        desktop_id = associate_ip_form.desktop_id.data
        
        fip = FloatingIpUtils.get_floating_ip_by_ref_id(fip_ref_id)
        desktop = Desktop.query.filter_by(id=desktop_id).first()
        if not fip:
            ret['status'] = 'fail'
            ret['data'] = '未找到该浮动IP'
        elif not desktop:
            ret['status'] = 'fail'
            ret['data'] = '未找到该云桌面'
        else:
            # first, we should modify the floating ip's status
            fip = FloatingIpUtils.allocate_floating_ip_by_ref_id(fip_ref_id)
            if not fip:
                ret['status'] = 'fail'
                ret['data'] = '该浮动IP正在使用中'
            else:
                vm_ref = desktop.vm_ref
                if not vm_ref:
                    ret['status'] = 'fail'
                    ret['data'] = '该云桌面不可用'
                    LOG.warning('Desktop <%s-%s> has no vm_ref' % (desktop.id, desktop.name))
                else:
                    success = False
                    # second, we try to associate fip with the desktop's ports
                    if is_neutron_network:
                        ports = utils.list_ports_by_instance(vm_ref)
                        for port in ports:
                            try:
                                OpenstackNetworkService.update_floatingip(fip_ref_id, {'floatingip': {'port_id': port['id']}})
                                ret['status'] = 'success'
                                success = True
                                ua_logger.info(current_user, '绑定浮动IP<%s>到云桌面<%s-%s>' % (fip.ip_address, desktop.id, desktop.name))
                                break
                            except Exception as ex:
                                LOG.exception('Associate ip "%s" with port "%s" fail' % (fip.ip_address, port['id']))
                                ret['status'] = 'error'
                                ret['message'] = str(ex)
                    else:
                        try:
                            OpenstackNetworkService.add_floating_ip(vm_ref, fip.ip_address)
                            ret['status'] = 'success'
                            success = True
                            ua_logger.info(current_user, '绑定浮动IP<%s>到云桌面<%s-%s>' % (fip.ip_address, desktop.id, desktop.name))
                        except Exception as ex:
                            LOG.exception('Associate ip "%s" with instance "%s" fail' % (fip.ip_address, vm_ref))
                            ret['status'] = 'error'
                            ret['message'] = str(ex)

                    if not success:
                        FloatingIpUtils.reclaim_floating_ip(fip.ip_address)
                    else:
                        # TODO: here need to use try excpet block, when raise exception, 
                        # disassociate the floating ip and set its status to DOWN
                        desktop.floating_ip = fip.ip_address
                        db.session.add(desktop)
                        db.session.commit()

    else:
        ret["status"] = "fail"
        ret["data"] = str(associate_ip_form.errors)
        LOG.warning("Associate ip form invalid: %s" % ret["data"])

    return jsonify(ret)


@network.route('/floatingips/release', methods=['DELETE'])
@login_required
def floatingips_release():
    ret = {'status': 'success', 'data': {"success_list":[], "fail_list": []}}

    fip_ref_ids = request.json
    nova_floatingips_dict = dict([(str(ip.id), ip.instance_id) for ip in \
        OpenstackNetworkService.list_floatingips()])
    for fip_ref_id in fip_ref_ids:
        vm_ref = nova_floatingips_dict.get(fip_ref_id)
        desktop = Desktop.query.filter_by(vm_ref=vm_ref).first() if vm_ref else None
        try:
            OpenstackNetworkService.delete_floating_ip(fip_ref_id)
            ret['data']['success_list'].append(fip_ref_id)
            ua_logger.info(current_user, '释放浮动IP "%s"' % fip_ref_id)
        except Exception as ex:
            LOG.exception('Release floating ip "%s" fail' % fip_ref_id)
            ret['data']['fail_list'].append({'ref_id': fip_ref_id, 'reason': str(ex)})
        else:
            # FIXME: if here raise exception, is it necessary to
            # recovery the floating ip?
            FloatingIpUtils.delete_floating_ip_by_ref_id(fip_ref_id)
            if desktop:
                desktop.floating_ip = None
                db.session.add(desktop)
                db.session.commit()

    return jsonify(ret)


@network.route('/floatingips/allocate', methods=['PUT'])
@login_required
def floatingip_allocate():
    ret = {'status': '', 'data': ''}

    allocate_ip_form = AllocateIPForm()
    if allocate_ip_form.validate_on_submit():
        fip_pool = allocate_ip_form.fip_pool.data
        try:
            fip = OpenstackNetworkService.allocate_floating_ip(fip_pool)

            floating_ip = FloatingIp(ref_id=fip['id'], ip_address=fip['ip'], external_network_id=fip['pool'], 
                                     status=FloatingIp.IP_STATUS.DOWN)
            FloatingIpUtils.create_floating_ip(floating_ip)
            ret['status'] = 'success'
            ret['data'] = fip['ip']
            ua_logger.info(current_user, '分配浮动IP "%s"' % fip['ip'])
        except Exception as ex:
            LOG.exception('Allocate floating ip from pool "%s" fail' % fip_pool)
            ret['status'] = 'error'
            ret['message'] = str(ex)

    else:
        ret['status'] = 'fail'
        ret['data'] = str(allocate_ip_form.errors)
        LOG.warning('Allocate ip form invalid: %s' % ret['data'])

    return jsonify(ret)


@network.route('/security_groups', methods=['GET'])
@login_required
def security_groups():
    security_groups = OpenstackNetworkService.list_security_groups(tenant_id=utils.get_tenant_id())
    security_group_create_form = SecurityGroupCreateForm()
    security_group_update_form = SecurityGroupUpdateForm()
    return render_template("network/security_group.html", security_groups=security_groups,
            sg_create_form=security_group_create_form,
            sg_update_form=security_group_update_form)


@network.route('/security_groups', methods=['PUT'])
@login_required
def create_security_group():
    ret = {'status': '', 'data': ''}

    sg_create_form = SecurityGroupCreateForm()
    if sg_create_form.validate_on_submit():
        name = sg_create_form.name.data.strip()
        description = sg_create_form.description.data.strip()

        # first, check whether the name is exist
        sg_name_list = [ sg['name'] for sg in OpenstackNetworkService.list_security_groups(tenant_id=utils.get_tenant_id())]
        if name in sg_name_list:
            ret['status'] = 'fail'
            ret['data'] = '安全组名称"%s"已经存在' % name
        else:
            try:
                OpenstackNetworkService.create_security_group(name, description)
            except Exception as ex:
                LOG.exception('Create security group "%s-%s" fail' % (name, description))
                ret['status'] = 'error'
                ret['message'] = str(ex)
            else:
                ret['status'] = 'success'
                ua_logger.info(current_user, '创建安全组 "%s"' % name)
                LOG.info('Create security group "%s-%s"' % (name, description))
    else:
        ret['status'] = 'fail'
        ret['data'] = str(sg_create_form.errors)
        LOG.warning('Security group create form invalid: %s' % ret['data'])

    return jsonify(ret)


@network.route('/security_groups', methods=['DELETE'])
@login_required
def delete_security_groups():
    ret = {'status': 'success', 'data': {"success_list":[], "fail_list": []}}

    sg_ids = request.json
    for sg_id in sg_ids:
        try:
            OpenstackNetworkService.delete_security_group(sg_id)
        except Exception as ex:
            # FIXME: if the security group not exist, here will raise novaclient's NotFound exception
            # or neutronclient's NotFound exception, we should distinguish and catch
            # novaclient's NotFound exception has code attribute;
            # neutronclient's NotFound exception has status_code attribute
            if getattr(ex, 'code', None) == 404 or getattr(ex, 'status_code', None) == 404:
                ret['data']['success_list'].append(sg_id)
            else:
                LOG.exception('Delete security group "%s" fail' % sg_id)
                ret['data']['fail_list'].append({'id': sg_id, 'reason': str(ex)})
        else:
            ua_logger.info(current_user, '删除安全组 "%s"' % sg_id)
            LOG.info('Delete security group "%s"' % sg_id)
            ret['data']['success_list'].append(sg_id)

    return jsonify(ret)


@network.route('/security_groups/update', methods=['PUT'])
@login_required
def update_security_group():
    ret = {'status': '', 'data': ''}

    sg_update_form = SecurityGroupUpdateForm()
    if sg_update_form.validate_on_submit():
        sg_id = sg_update_form.ID.data
        sg_name = sg_update_form.name.data
        sg_desc = sg_update_form.description.data
        
        try:
            OpenstackNetworkService.update_security_group(sg_id, sg_name, sg_desc)
        except Exception as ex:
            LOG.exception('Update security group "%s" fail' % sg_id)
            ret['status'] = 'error'
            ret['message'] = str(ex)
        else:
            ret['status'] = 'success'
            ua_logger.info(current_user, '编辑安全组 "%s-%s"' % (sg_id, sg_name))
            LOG.info('Update security group "%s"' % sg_id)
    else:
        ret['status'] = 'fail'
        ret['data'] = str(sg_update_form.errors)
        LOG.warning('Security group update form invalid: %s' % ret['data'])

    return jsonify(ret)


@network.route('/security_groups/<string:id>', methods=['GET'])
@login_required
def security_group_detail(id):
    try:
        secgroup = OpenstackNetworkService.show_security_group(id)
        secgroup['rules'] = sorted(secgroup['rules'], key=lambda rule: (rule['ip_protocol'], rule['from_port'] or -1))
    except Exception as ex:
        code = getattr(ex, 'code', None) or getattr(ex, 'status_code', None)
        if code == 404 or code == 400:
            abort(404)
        else:
            LOG.exception('Get security group "%s" detail fail' % id)
            abort(500)
    else:
        for rule in secgroup['rules']:
            port_range = utils.get_port_range(rule)
            rule['port_range'] = port_range

        sg_rule_create_form = SecgroupRuleCreateForm(secgroup_id=id)
        return render_template('network/security_group_detail.html', secgroup=secgroup, sgr_create_form=sg_rule_create_form)


@network.route('/security_groups/rules', methods=['PUT'])
@login_required
def create_secgroup_rule():
    ret = {'status':'', 'data': ''}

    sgr_create_form = SecgroupRuleCreateForm()
    if sgr_create_form.validate_on_submit():
        try:
            data = sgr_create_form.data
            OpenstackNetworkService.create_security_group_rule(data['ID'], data['direction'], data['ethertype'], data['ip_protocol'],
                                                               data['from_port'], data['to_port'], data['cidr'], data['security_group'])
        except Exception as ex:
           LOG.exception('Create security group rule fail')
           ret['status'] = 'error'
           ret['message'] = str(ex)
        else:
            ret['status'] = 'success'
            ua_logger.info(current_user, '添加安全组"%s"规则' % data['ID'])
            LOG.info('Create security group rule %s' % data['ID'])
    else:
        ret['status'] = 'fail'
        ret['data'] = str(sgr_create_form.errors)
        LOG.warning('Create secgroup rule form invalid: %s' % ret['data'])
    
    return jsonify(ret)


@network.route('/security_groups/rules', methods=['DELETE'])
@login_required
def delete_secgroup_rules():
    ret = {'status': 'success', 'data': {"success_list":[], "fail_list": []}}

    sgr_ids = request.json
    for sgr_id in sgr_ids:
        try:
            OpenstackNetworkService.delete_security_group_rule(sgr_id)
        except Exception as ex:
            # FIXME: if the security group not exist, here will raise novaclient's NotFound exception
            # or neutronclient's NotFound exception, we should distinguish and catch
            # novaclient's NotFound exception has code attribute;
            # neutronclient's NotFound exception has status_code attribute
            if getattr(ex, 'code', None) == 404 or getattr(ex, 'status_code', None) == 404:
                ret['data']['success_list'].append(sgr_id)
            else:
                LOG.exception('Delete security group rule "%s" fail' % sgr_id)
                ret['data']['fail_list'].append({'id': sgr_id, 'reason': str(ex)})
        else:
            ua_logger.info(current_user, '删除安全组规则 "%s"' % sgr_id)
            LOG.info('Delete security group rule "%s"' % sgr_id)
            ret['data']['success_list'].append(sgr_id)

    return jsonify(ret)





