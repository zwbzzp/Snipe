# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# comment
#
# 2016/7/7 chengkang : Init

from flask import render_template, request, jsonify, abort, current_app, redirect, url_for
from flask.ext.login import login_required, current_user
from . import network
from .forms import NetworkUpdateForm, NetworkCreateForm, PortCreateForm, PortUpdateForm, RouterCreateForm, \
                RouterAddGatewayForm, RouterAddInterfaceForm, SubnetCreateForm, SubnetUpdateForm
from . import utils
from ..models import Desktop, Course, User

from phoenix.cloud import network as OpenstackNetworkService
from phoenix.cloud import compute as OpenstackComputeService
from neutronclient.common.exceptions import NotFound, PortNotFoundClient
from ..log.utils import UserActionLogger
import logging

LOG = logging.Logger(__name__)
ua_logger = UserActionLogger()


@network.route('/topology', methods=['GET'])
@login_required
def network_topology():
    # Get nova data
    # here we get the local desktop data instead of nova data
    try:
        desktops = Desktop.query.all()
    except Exception:
        desktops = []
    servers = [{'name': desktop.name, 'id': desktop.vm_ref}
                for desktop in desktops if desktop.vm_ref]

    # Get neutron data
    # if we didn't specify tenant_id, all networks shown as admin user.
    # so it is need to specify the networks. However there is no need to
    # specify tenant_id for subnet. The subnet which belongs to the public
    # network is needed to draw subnet information on public network.
    try:
        neutron_networks = utils.network_list_for_tenant()
        neutron_public_networks = utils.list_external_networks()
        neutron_ports = OpenstackNetworkService.list_ports().get('ports')
        neutron_routers = utils.router_list_for_tenant()
    except Exception:
        neutron_networks = []
        neutron_public_networks = []
        neutron_ports = []
        neutron_routers = []

    for network in neutron_networks:
        nn = network
    networks = [{'name': network['name'], 'id': network['id'],
                 'subnets': [{'id': subnet['id'], 'name': subnet['name'], 'enable_dhcp': subnet['enable_dhcp'], 'ip_version': subnet['ip_version'], 'cidr': subnet['cidr'], 'allocation_pools': [{'start':pool["start"], 'end':pool["end"]} for pool in subnet['allocation_pools']] , 'gateway_ip': subnet['gateway_ip'], 'enable_dhcp': subnet['enable_dhcp'] } for subnet in network["subnets"]],
                'router:external': network['router:external'], 'can_access': True} 
                for network in neutron_networks]

    external_network_detail = []

    for publicnet in neutron_public_networks:
        found = False
        for network in networks:
            if publicnet['id'] == network['id']:
                found = True
                break
        if not found:
            try:
                subnets = [{'cidr': subnet['cidr']}
                            for subnet in publicnet["subnets"]]
            except Exception:
                subnets = []

            networks.append({
                'name': publicnet['name'],
                'id': publicnet['id'],
                'subnets': subnets,
                'router:external': publicnet['router:external'],
                'can_access': False})
            external_network_detail.append({
                'name': publicnet['name'],
                'id': publicnet['id'],
                'routers': [],
                'inter_network': []})
    networks = sorted(networks, key=lambda x: x.get('router:external'), reverse=True)
    for network in networks:
        network['courses'] = []
        courses = Course.query.filter_by(network_ref=network['id'])
        for course in courses:
            course_owner = User.query.filter_by(id=course.owner_id).first().username
            desktops = Desktop.query.filter_by(course_id=course.id).all()
            desktop_count = 0
            for desktop in desktops:
                if desktop.vm_ref:
                    desktop_count = desktop_count + 1
            network['courses'].append({'name': course.name, 'id': course.id, 'desktop_count': desktop_count})

    ports = [{'id': port['id'], 'network_id': port['network_id'], 'device_id': port['device_id'],
                'fixed_ips': port['fixed_ips'], 'device_owner': port['device_owner'], 'status': port['status']}
            for port in neutron_ports]

    routers = [{'id': router['id'], 'name': router['name'], 'status': router['status'], 'external_gateway_info': router['external_gateway_info']}
                for router in neutron_routers]


    def _check_router_external_port(ports, router_id, network_id):
        for port in ports:
            if port['network_id'] == network_id and port['device_id'] == router_id:
                return True
        return False

    def _get_network_from_list(network_list, network_id):
        for network in network_list:
            if network.get('id') == network_id:
                return network
        return None

    # user can't see port on external network.
    # so we are adding fake port based on router information
    for router in routers:
        external_gateway_info = router.get('external_gateway_info')
        if not external_gateway_info:
            continue
        external_network = external_gateway_info.get('network_id')
        if not external_network:
            continue
        if _check_router_external_port(ports, router['id'], external_network):
            continue

        fake_port = {'id': 'gateway%s' % external_network,
                     'network_id': external_network,
                     'device_id': router['id'],
                     'device_owner': 'network:router_gateway',
                     'fixed_ips': []}
        ports.append(fake_port)
        for external_network in external_network_detail:
            if external_network['id'] == external_network['id']:
                external_network['routers'].append({
                    'id': router['id'],
                    'name': router['name']})

    island_servers = [] # the set of the servers which not connect to any networks
    for server in servers:
        found = False
        for port in ports:
            if port["device_id"] == server["id"]:
                found = True
                network = _get_network_from_list(networks, port["network_id"])
                if network:
                    server_num = network.get("server_num")
                    if server_num:
                        network["server_num"] += 1
                    else:
                        network["server_num"] = 1
        if not found:
            island_servers.append(island_servers)

    def _find_internetwork(network_id):
        for net in networks:
            if net['id'] == network_id:
                return net
        return None

    def _find_internetwork_exist(network_list, network_id):
        for net in network_list:
            if net['id'] == network_id:
                return True
        return False

    for external_network in external_network_detail:
        for router in external_network['routers']:
            for port in ports:
                if port['device_id'] == router['id'] and port['network_id'] != external_network['id']:
                    if not _find_internetwork_exist(external_network['inter_network'], port['network_id']):
                        net = _find_internetwork(port['network_id'])
                        if net:
                            server_num = 0
                            if net.get("server_num"):
                                server_num = net['server_num']
                            external_network['inter_network'].append({
                                'name': net['name'],
                                'id': net['id'],
                                'server_num': server_num})

        for network in external_network['inter_network']:
            network['courses'] = []
            courses = Course.query.filter_by(network_ref=network['id'])
            for course in courses:
                course_owner = User.query.filter_by(id=course.owner_id).first().username
                desktops = Desktop.query.filter_by(course_id=course.id).all()
                desktop_count = 0
                for desktop in desktops:
                    if desktop.vm_ref:
                        desktop_count = desktop_count + 1
                network['courses'].append({'name': course.name, 'id': course.id, 'desktop_count': desktop_count})

    return render_template('network/network_topology.html', networks=networks, routers=routers, ports=ports, island_servers=island_servers, external_network_detail = external_network_detail)


@network.route('/networks', methods=['GET'])
@login_required
def networks():
    # TODO: currently we provide network management service only when the openstack use neutron network
    if not OpenstackNetworkService.is_neutron_network():
        abort(404)

    try:
        networks = utils.network_list_for_tenant()
    except Exception as ex:
        LOG.exception(ex)
        abort(404)

    network_update_form = NetworkUpdateForm()
    network_create_form = NetworkCreateForm()
    return render_template('network/network.html',
                            networks=networks,
                            network_update_form=network_update_form,
                            network_create_form=network_create_form)


@network.route('/networks', methods=['PUT'])
@login_required
def create_network():
    ret = {"status": "", "data": ""}

    network_create_form = NetworkCreateForm()
    if network_create_form.validate_on_submit():
        name = network_create_form.name.data
        admin_state_up = network_create_form.admin_state_up.data
        create_subnet = network_create_form.create_subnet.data
        
        try:
            body = {"network": {"name": name, "admin_state_up": admin_state_up}}
            network = OpenstackNetworkService.create_network(body).get("network")
        except Exception as ex:
            ret["status"] = "error"
            ret["message"] = str(ex)
            LOG.warning('Failed to create network "%(network)s": %(reason)s' % {"network": name, "reason": ex})
        else:
            if create_subnet:
                subnet_name = network_create_form.subnet_name.data
                subnet_cidr = network_create_form.subnet_cidr.data
                subnet_ip_version = network_create_form.ip_version.data
                subnet_gateway_ip = network_create_form.gateway_ip.data
                subnet_disable_gateway = network_create_form.disable_gateway.data
                subnet_enable_dhcp = network_create_form.enable_dhcp.data
                subnet_allocation_pools = network_create_form.allocation_pools.data
                subnet_dns_nameservers = network_create_form.dns_nameservers.data
                subnet_host_routes = network_create_form.host_routes.data

                try:
                    data = {"network_id": network["id"], "name": subnet_name, "cidr": subnet_cidr, 
                                "ip_version": int(subnet_ip_version), "enable_dhcp": subnet_enable_dhcp,
                                 "disable_gateway": subnet_disable_gateway, "gateway_ip": subnet_gateway_ip,
                                 "allocation_pools": subnet_allocation_pools, "host_routes": subnet_host_routes,
                                 "dns_nameservers": subnet_dns_nameservers}

                    subnet = utils.create_subnet(data)
                    ret["status"] = "success"
                    ua_logger.info(current_user, "创建网络[%(net_id)s-%(net_name)s]+子网[%(sub_id)s-%(sub_name)s]" %
                                    {"net_id": network["id"], "net_name": network["name"], "sub_id": subnet["id"], "sub_name": subnet["name"]})
                except Exception as ex:
                    ret["status"] = "error"
                    ret["message"] = str(ex)
                    LOG.warning('Failed to create subnet "%(subnet)s": %(reason)s' % {"subnet": subnet_name, "reason": ex})

                    try:
                        OpenstackNetworkService.delete_network(network["id"])
                    except Exception as ex:
                        LOG.warning("Failed to delete network: %s-%s" % (network["id"], network["name"]))
            else:
                ret["status"] = "success"
                ua_logger.info(current_user, "创建网络: %(net_id)s-%(net_name)s" % {"net_id": network["id"], "net_name": network["name"]})
    else:
        ret["status"] = "fail"
        ret["data"] = str(network_create_form.errors)
        LOG.warning("Create network form invalid: %s" % ret["data"])

    return jsonify(**ret)


@network.route('/networks/update', methods=['PUT'])
@login_required
def update_network():
    ret = {"status": "", "data": ""}

    network_update_form = NetworkUpdateForm()
    if network_update_form.validate_on_submit():
        name = network_update_form.name.data
        ID = network_update_form.ID.data
        admin_state_up = network_update_form.admin_state_up.data
        try:
            OpenstackNetworkService.update_network(ID, {"network": {"name": name, "admin_state_up": admin_state_up}})
            ret["status"] = "success"
            ua_logger.info(current_user, "update network[%s] name->%s" % (ID, name))
        except Exception as ex:
            ret["status"] = "error"
            if getattr(ex, "status_code", None) == 404:
                ret["message"] = "该网络未找到"
            else:
                ret["message"] = str(ex)
            LOG.warning("update network[%s] error: %s" % (ID, ret["message"]))
    else:
        ret["status"] = "fail"
        ret["data"] = str(network_update_form.errors)
        LOG.warning("update network fail: %s" % ret["data"])

    return jsonify(**ret)


@network.route('/networks/delete', methods=['DELETE'])
@login_required
def delete_networks():
    ret = {"status": "success", "data": {"success_list":[], "fail_list": []}}

    delete_network_ids = request.json
    for network_id in delete_network_ids:
        try:
            OpenstackNetworkService.delete_network(network_id)
            ret["data"]["success_list"].append(network_id)
            ua_logger.info(current_user, "delete network %s" % network_id)
        except Exception as ex:
            if getattr(ex, "status_code", None) == 404:
                ret["data"]["success_list"].append(network_id)
            else:
                reason = str(ex)
                ret["data"]["fail_list"].append({"id": network_id, "reason": reason})

    return jsonify(**ret)


@network.route('/networks/<string:id>/detail', methods=['GET'])
@login_required
def network_detail(id):
    # first, check whether the network exist
    try:
        network_info = OpenstackNetworkService.show_network(id).get("network")
    except Exception as ex:
        LOG.error("fetch network[%s] info fail: %s" % (id, str(ex)))
        abort(404)
    else:
        if not network_info:
            LOG.warning("fetch network[%s] info fail: return is None" % id)
            abort(404)

    # second, check  whether current tenant has the right to get the network's detail
    def can_access():
        neutron_networks = utils.network_list_for_tenant()
        can = False
        for network in neutron_networks:
            if network['id'] == id:
                can = True
                break
        return can
    try:
        can = can_access()
    except Exception as ex:
        LOG.error("check whether has right to get network[%s] info fail: %s" % (id, str(ex)))
        abort(404)
    else:
        if not can:
            abort(403)

    try:
        subnets_info = OpenstackNetworkService.list_subnets(network_id=network_info["id"]).get("subnets", None)
        ports_info = OpenstackNetworkService.list_ports(network_id=network_info["id"]).get("ports", None)
    except Exception as ex:
        LOG.error("fetch network[%s]'s subnets and ports info fail: %s" % (id, str(ex)))
        abort(404)

    port_create_form = PortCreateForm()
    port_update_form = PortUpdateForm()
    subnet_create_form = SubnetCreateForm()
    subnet_update_form = SubnetUpdateForm()

    return render_template('network/network_detail.html',
                            network_info=network_info,
                            subnets_info=subnets_info,
                            ports_info=ports_info,
                            port_create_form=port_create_form,
                            port_update_form=port_update_form,
                            subnet_create_form=subnet_create_form,
                            subnet_update_form=subnet_update_form)

@network.route('/networks/<string:id>/detail_info', methods=['GET'])
@login_required
def network_detail_info(id):
    # first, check whether the network exist
    try:
        network_info = OpenstackNetworkService.show_network(id).get("network")
    except Exception as ex:
        LOG.error("fetch network[%s] info fail: %s" % (id, str(ex)))
        abort(404)
    else:
        if not network_info:
            LOG.warning("fetch network[%s] info fail: return is None" % id)
            abort(404)

    # second, check  whether current tenant has the right to get the network's detail
    def can_access():
        neutron_networks = utils.network_list_for_tenant()
        can = False
        for network in neutron_networks:
            if network['id'] == id:
                can = True
                break
        return can
    try:
        can = can_access()
    except Exception as ex:
        LOG.error("check whether has right to get network[%s] info fail: %s" % (id, str(ex)))
        abort(404)
    else:
        if not can:
            abort(403)

    try:
        subnets_info = OpenstackNetworkService.list_subnets(network_id=network_info["id"]).get("subnets", None)
        ports_info = OpenstackNetworkService.list_ports(network_id=network_info["id"]).get("ports", None)
    except Exception as ex:
        LOG.error("fetch network[%s]'s subnets and ports info fail: %s" % (id, str(ex)))
        abort(404)

    port_create_form = PortCreateForm()
    port_update_form = PortUpdateForm()
    subnet_create_form = SubnetCreateForm()
    subnet_update_form = SubnetUpdateForm()

    return render_template('network/network_info.html',
                            network_info=network_info,
                            subnets_info=subnets_info,
                            ports_info=ports_info,
                            port_create_form=port_create_form,
                            port_update_form=port_update_form,
                            subnet_create_form=subnet_create_form,
                            subnet_update_form=subnet_update_form)
    # return jsonify(subnets_info)

@network.route('/ports', methods=['PUT'])
@login_required
def create_port():
    ret = {"status": "", "data": ""}

    port_create_form = PortCreateForm()
    if port_create_form.validate_on_submit():
        try:
            body = {"port": {}}
            params = ["network_id", "name", "admin_state_up", "device_id", "device_owner"]
            for param in params:
                value = getattr(port_create_form, param).data
                body["port"][param] = value

            port = OpenstackNetworkService.create_port(body).get("port", None)
            ret["status"] = "success"
            ua_logger.info(current_user, "create port[%s] %s" % (port["id"] if port else None, port["name"] if port else body["port"]["name"]))
        except Exception as ex:
            LOG.exception(ex)
            ret["status"] = "error"
            ret["message"] = str(ex)
    else:
        ret["status"] = "fail"
        ret["data"] = str(port_create_form.errors)
        LOG.warning("create port fail: %s" % ret["data"])

    return jsonify(**ret)


@network.route('/ports', methods=['DELETE'])
@login_required
def delete_ports():
    ret = {"status": "success", "data": {"success_list":[], "fail_list": []}}

    delete_port_ids = request.json
    for port_id in delete_port_ids:
        try:
            OpenstackNetworkService.delete_port(port_id)
            ret["data"]["success_list"].append(port_id)
            ua_logger.info(current_user, "delete port %s" % port_id)
        except Exception as ex:
            if getattr(ex, "status_code", None) == 404:
                ret["data"]["success_list"].append(port_id)
            else:
                reason = str(ex)
                ret["data"]["fail_list"].append({"id": port_id, "reason": reason})

    return jsonify(**ret)


@network.route('/ports/update', methods=['PUT'])
@login_required
def update_port():
    ret = {"status": "", "data": ""}

    port_update_form = PortUpdateForm()
    if port_update_form.validate_on_submit():
        try:
            port_id = port_update_form.port_id.data
            body = {"port": {}}
            params = ["name", "admin_state_up", "device_id", "device_owner"]
            for param in params:
                value = getattr(port_update_form, param).data
                body["port"][param] = value 

            port = OpenstackNetworkService.update_port(port_id, body).get("port", None)
            ret["status"] = "success"
            ua_logger.info(current_user, "update port %s" % (port["id"] if port else port_id))
        except Exception as ex:
            ret["status"] = "error"
            if getattr(ex, "status_code", None) == 404:
                ret["message"] = "该端口未找到"
            else:
                ret["message"] = str(ex)
            LOG.warning("update port[%s] error: %s" % (port_id, ret["message"]))
    else:
        ret["status"] = "fail"
        ret["data"] = str(port_update_form.errors)
        LOG.warning("Update port fail: %s" % ret["data"])

    return jsonify(**ret)


@network.route('/subnets', methods=['PUT'])
@login_required
def create_subnet():
    ret = {"status": "", "data": ""}

    subnet_create_form = SubnetCreateForm()
    if subnet_create_form.validate_on_submit():
        data = {}
        from wtforms import Field
        for attr in dir(subnet_create_form):
            obj = getattr(subnet_create_form, attr, None)
            if isinstance(obj, Field):
                data[attr] = obj.data

        try:
            subnet = utils.create_subnet(data)
            ret["status"] = "success"
            ua_logger.info(current_user, "在网络[%(net_id)s]下创建子网[%(sub_id)s-%(sub_name)s]" %
                                        {"net_id": data["network_id"], "sub_id": subnet["id"], "sub_name": subnet["name"]})
        except Exception as ex:
            ret["status"] = "error"
            ret["message"] = str(ex)
            LOG.warning('Failed to create subnet "%(subnet)s": %(reason)s' % {"subnet": data["name"], "reason": ex})
    else:
        ret["status"] = "fail"
        ret["data"] = str(subnet_create_form.errors)
        LOG.warning("Create subnet fail: %s" % ret["data"])

    return jsonify(**ret)  


@network.route('/subnets/update', methods=['PUT'])
@login_required
def update_subnet():
    ret = {"status": "", "data": ""}

    subnet_update_form = SubnetUpdateForm()
    if subnet_update_form.validate_on_submit():
        data = {}
        from wtforms import Field
        for attr in dir(subnet_update_form):
            obj = getattr(subnet_update_form, attr, None)
            if isinstance(obj, Field):
                data[attr] = obj.data

        try:
            subnet_name = data["name"]
            subnet = utils.update_subnet(data)
            ret["status"] = "success"
            ua_logger.info(current_user, "编辑子网[%(id)s-%(name)s-%(cidr)s]" % {"id": subnet["id"], "name": subnet["name"], "cidr": subnet["cidr"]})
        except Exception as ex:
            ret["status"] = "error"
            ret["message"] = str(ex)
            LOG.warning('Failed to update subnet "%(subnet)s": %(reason)s' % {"subnet": subnet_name, "reason": ex})
    else:
        ret["status"] = "fail"
        ret["data"] = str(subnet_update_form.errors)
        LOG.warning("Update subnet fail: %s" % ret["data"])

    return jsonify(**ret)


@network.route('/subnets', methods=['DELETE'])
@login_required
def delete_subnets():
    ret = {"status": "success", "data": {"success_list":[], "fail_list": []}}

    delete_subnet_ids = request.json
    for subnet_id in delete_subnet_ids:
        try:
            OpenstackNetworkService.delete_subnet(subnet_id)
            ret["data"]["success_list"].append(subnet_id)
            ua_logger.info(current_user, "delete subnet %s" % subnet_id)
        except Exception as ex:
            if getattr(ex, "status_code", None) == 404:
                ret["data"]["success_list"].append(subnet_id)
            else:
                reason = str(ex)
                ret["data"]["fail_list"].append({"id": subnet_id, "reason": reason})

    return jsonify(**ret)


@network.route('/routers', methods=['GET'])
@login_required
def routers():
    # TODO: currently we provide network management service only when the openstack use neutron network
    if not OpenstackNetworkService.is_neutron_network():
        abort(404)

    try:
        neutron_routers = utils.router_list_for_tenant()
        for router in neutron_routers:
            external_gateway_info = router.get("external_gateway_info")
            router["external_network"] = None
            if external_gateway_info:
                external_network_id = external_gateway_info.get("network_id")
                if external_network_id:
                    external_network_name = utils.get_network_name_by_id(external_network_id)
                    if external_network_name:
                        router["external_network"] = external_network_name

    except Exception as ex:
        LOG.exception(ex)
        abort(404)

    router_create_form = RouterCreateForm()
    router_add_gateway_form = RouterAddGatewayForm()
    return render_template("network/router.html",
                            routers=neutron_routers,
                            router_create_form=router_create_form,
                            router_add_gateway_form=router_add_gateway_form)


@network.route('/routers', methods=['PUT'])
@login_required
def create_router():
    ret = {"status": "", "data": ""}

    router_create_form = RouterCreateForm()
    if router_create_form.validate_on_submit():
        try:
            body = {"router": {}}
            params = ["name"]
            for param in params:
                value = getattr(router_create_form, param).data
                body["router"][param] = value

            router = OpenstackNetworkService.create_router(body).get("router")
            ret["status"] = "success"
            ua_logger.info(current_user, "新建路由[%s]:%s" % (router["id"], router["name"]))
        except Exception as ex:
            LOG.exception(ex)
            ret["status"] = "error"
            ret["message"] = str(ex)
    else:
        ret["status"] = "fail"
        ret["data"] = str(router_create_form.errors)
        LOG.warning("create router fail: %s" % ret["data"])

    return jsonify(**ret)


@network.route('/routers', methods=['DELETE'])
@login_required
def delete_routers():
    ret = {"status": "success", "data": {"success_list":[], "fail_list": []}}

    delete_router_ids = request.json
    for router_id in delete_router_ids:
        try:
            OpenstackNetworkService.delete_router(router_id)
            ret["data"]["success_list"].append(router_id)
            ua_logger.info(current_user, "删除路由 %s" % router_id)
        except Exception as ex:
            LOG.exception(ex)
            if getattr(ex, "status_code", None) == 404:
                ret["data"]["success_list"].append(router_id)
            else:
                reason = str(ex)
                ret["data"]["fail_list"].append({"id": router_id, "reason": reason})

    return jsonify(**ret)


@network.route('/routers/remove_gateways', methods=['DELETE'])
@login_required
def remove_gateway_routers():
    ret = {"status": "success", "data": {"success_list":[], "fail_list": []}}

    remove_gateway_router_ids = request.json
    for router_id in remove_gateway_router_ids:
        try:
            router = OpenstackNetworkService.remove_gateway_router(router_id).get("router")
            ret["data"]["success_list"].append(router_id)
            ua_logger.info(current_user, "清除路由网关 %s %s" % (router_id, router["name"] if router else None))
        except Exception as ex:
            LOG.exception(ex)
            reason = str(ex)
            if getattr(ex, "status_code", None) == 404:
                reason = "该路由未找到"

            ret["data"]["fail_list"].append({"id": router_id, "reason": reason})

    return jsonify(**ret)


@network.route('/routers/add_gateway', methods=['PUT'])
@login_required
def add_gateway_router():
    ret = {"status": "", "data": ""}

    router_add_gateway_form = RouterAddGatewayForm()
    if router_add_gateway_form.validate_on_submit():
        router_id = router_add_gateway_form.router_id.data
        external_network_id = router_add_gateway_form.external_network_id.data
        try:
            router = OpenstackNetworkService.add_gateway_router(router_id, {"network_id": external_network_id}).get("router")
            ret["status"] = "success"
            ua_logger.info(current_user, "设置路由[%s]网关: 外部网络[%s]" % (router_id, external_network_id))
        except Exception as ex:
            LOG.warning("add gateway[%s] for router[%s] raise error: %s" %
                                    (external_network_id, router_id, str(ex)))
            ret["status"] = "error"
            ret["message"] = str(ex)
    else:
        ret["status"] = "fail"
        ret["data"] = str(router_add_gateway_form.errors)
        LOG.warning("add gateway router fail: %s" % ret["data"])

    return jsonify(**ret)


@network.route('/routers/<string:id>/detail', methods=['GET'])
@login_required
def router_detail(id):
    # first, check whether the router exist
    try:
        router_info = OpenstackNetworkService.show_router(id).get("router")
    except Exception as ex:
        LOG.error("fetch router[%s] info fail: %s" % (id, str(ex)))
        abort(404)
    else:
        if not router_info:
            LOG.warning("fetch router[%s] info fail: return is None" % id)
            abort(404)

    # second, check  whether current tenant has the right to get the router's detail
    def can_access():
        neutron_routers = utils.router_list_for_tenant()
        can = False
        for router in neutron_routers:
            if router['id'] == id:
                can = True
                break
        return can
    try:
        can = can_access()
    except Exception as ex:
        LOG.error("check whether has right to get router[%s] info fail: %s" % (id, str(ex)))
        abort(404)
    else:
        if not can:
            abort(403)
    
    # get the external gateway info 
    external_gateway_info = router_info.get("external_gateway_info")
    if external_gateway_info:
        external_network_id = external_gateway_info.get("network_id")
        if external_network_id:
            external_network_name = utils.get_network_name_by_id(external_network_id)
            if external_network_name:
                router_info["external_network"] = external_network_name

    try:
        # get the router's interface list
        search_opts = {"device_id": router_info["id"]}
        interface_list = OpenstackNetworkService.list_ports(**search_opts).get("ports")
    except Exception as ex:
        LOG.error("fetch router[%s]'s interface info fail: %s" % (id, str(ex)))
        abort(404)
            
    router_add_interface_form = RouterAddInterfaceForm()
    return render_template('network/router_detail.html',
                            router_info=router_info,
                            interface_list=interface_list,
                            router_add_interface_form=router_add_interface_form)


@network.route('/routers/remove_interfaces', methods=['DELETE'])
@login_required
def remove_interface_routers():
    ret = {"status": "success", "data": {"success_list":[], "fail_list": []}}
    
    remove_interface_router_ids = request.json
    router_id = request.json.get("router_id")
    interface_ids = request.json.get("interface_ids")

    if not router_id or not interface_ids:
        ret["status"] = "fail"
        ret["data"] = "missing necessary parameters"
        LOG.warning("remove interfaces of router missing necessary parameters")
    else:
        for interface_id in interface_ids:
            try:
                OpenstackNetworkService.remove_interface_router(router_id, {"port_id": interface_id})
                ret["data"]["success_list"].append(interface_id)
                ua_logger.info(current_user, "删除路由[%s]接口[%s]" % (router_id, interface_id))
            except PortNotFoundClient as ex:
                ret["data"]["success_list"].append(interface_id)
                LOG.warning("remove interface[%s] of router[%s] raise error: %s" % (interface_id, router_id, str(ex)))
            except NotFound as ex:
                reason = "路由未找到"
                ret["data"]["fail_list"].append({"id": interface_id, "reason": reason})
                LOG.warning("remove interface[%s] of router[%s] raise error: %s" % (interface_id, router_id, str(ex)))     
            except Exception as ex:
                reason = str(ex)
                ret["data"]["fail_list"].append({"id": interface_id, "reason": reason})
                LOG.warning("remove interface[%s] of router[%s] raise error: %s" % (interface_id, router_id, reason))

    return jsonify(**ret)


@network.route('/routers/add_interface', methods=['PUT'])
@login_required
def add_interface_router():
    ret = {"status": "", "data": ""}

    router_add_interface_form = RouterAddInterfaceForm()
    if router_add_interface_form.validate_on_submit():
        router_id = router_add_interface_form.router_id.data
        subnet_id = router_add_interface_form.subnet_id.data
        ip_address = router_add_interface_form.ip_address.data               

        if ip_address:
            try:
                subnet = OpenstackNetworkService.show_subnet(subnet_id).get("subnet")
            except Exception as ex:
                ret["status"] = "error"
                ret["message"] = str(ex)
                LOG.warning("fetch subnet[%s] info raise error: %s" % (subnet_id, str(ex)))
            else:
                network_id = subnet.get("network_id")
                body = {"port": {"network_id": network_id,
                            "fixed_ips": [{"subnet_id": subnet_id, "ip_address": ip_address}]}}
                try:
                    port = OpenstackNetworkService.create_port(body).get("port")
                except Exception as ex:
                    ret["status"] = "error"
                    ret["message"] = str(ex)
                    LOG.warning("create port[%s] raise error: %s" % (body, str(ex)))
                else:
                    try:
                        body = {"port_id": port["id"]}
                        interface = OpenstackNetworkService.add_interface_router(router_id, body)
                        ret["status"] = "success"
                        ua_logger.info(current_user, "为路由[%s]增加接口[%s]" % (router_id, port["id"]))
                    except Exception as ex:
                        ret["status"] = "error"
                        ret["message"] = str(ex)
                        LOG.warning("add interface[%s] for router[%s] raise error: %s" % (port["id"], router_id, str(ex)))
        else:
            try:
                body = {"subnet_id": subnet_id}
                interface = OpenstackNetworkService.add_interface_router(router_id, body)
                ret["status"] = "success"
                ua_logger.info(current_user, "为路由[%s]增加接口[%s]" % (router_id, interface["port_id"]))
            except Exception as ex:
                ret["status"] = "error"
                ret["message"] = str(ex)
                LOG.warning("add interface[%s] for router[%s] raise error: %s" % (body, router_id, str(ex)))
    else:
        ret["status"] = "fail"
        ret["data"] = str(router_add_interface_form.errors)
        LOG.warning("add interface router fail: %s" % ret["data"])

    return jsonify(**ret)