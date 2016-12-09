# -*- encoding: utf-8 -*-
# Copyrigt 2016 Vinzor Co.,Ltd.
#
# Network utils
#
# 2016/7/11 chengkang : Init

from phoenix.cloud import network as OpenstackNetworkService
from phoenix.cloud.openstack.client import ClientManager
from . import settings


def get_network_name_by_id(network_id):
    """
    Fetch a certain network's name
    Some networks have no names, we use the '(id)' as their names.
    """
    name = None

    network = OpenstackNetworkService.show_network(network_id).get("network")
    name = "(" + network_id + ")"
    if network:
        network_name = network.get("name")
        if network_name:
            name = network_name

    return name


def get_tenant_id():
    """
    Fetch current tenant's id
    """

    keystone_client = ClientManager().keystone_client
    tenant_id = keystone_client.tenant_id

    return tenant_id


def network_list(**params):
    networks = OpenstackNetworkService.list_networks(**params).get("networks")

    subnets = OpenstackNetworkService.list_subnets().get("subnets", [])
    subnet_dict = dict([(s['id'], s) for s in subnets])
    for n in networks:
        n["subnets"] = [subnet_dict.get(s) for s in n.get("subnets", [])]

    return networks


def network_list_for_tenant(**params):
    """
    Fetch network list for current tenant
    """
    tenant_id = get_tenant_id()

    networks = network_list(tenant_id=tenant_id, shared=False, **params)
    networks += network_list(shared=True, **params)

    return networks


def list_internal_networks():
    """
    Fetch all the networks except external
    """
    search_opts = {"router:external": False}

    internal_net_list = network_list(**search_opts)

    return internal_net_list


def list_external_networks():
    """
    Fetch all the external networks
    """
    search_opts = {"router:external": True}

    external_net_list = network_list(**search_opts)

    return external_net_list


def router_list_for_tenant(**params):
    """
    Fetch router list for current tenant
    """
    tenant_id = get_tenant_id()

    routers = OpenstackNetworkService.list_routers(tenant_id=tenant_id, **params).get('routers')

    return routers


def _setup_subnet_parameters(params, data, is_create=True):
    """Setup subnet parameters

    This methods setups subnet parameters which are available
    in both create and update.
    """
    is_update = not is_create
    params['enable_dhcp'] = data['enable_dhcp']

    disable_gateway = data["disable_gateway"]
    gateway_ip = data.get("gateway_ip")
    if disable_gateway:
        params["gateway_ip"] = None
    elif gateway_ip:
        params["gateway_ip"] = gateway_ip

    allocation_pools = data.get("allocation_pools")
    if is_create and allocation_pools:
        pools = [dict(zip(["start", "end"], pool.strip().split(',')))
                     for pool in allocation_pools.split('\n')
                        if pool.strip()]
        params["allocation_pools"] = pools

    host_routes = data.get("host_routes", '')
    if host_routes or is_update:
        routes = [dict(zip(["destination", "nexthop"], route.strip().split(',')))
                    for route in host_routes.split('\n')
                        if route.strip()]
        params["host_routes"] = routes

    dns_nameservers = data.get("dns_nameservers", '')
    if dns_nameservers or is_update:
        nameservers = [ns.strip()
                            for ns in dns_nameservers.split('\n')
                                if ns.strip()]
        params["dns_nameservers"] = nameservers


def create_subnet(data):
    """
    Create a subnet
    """
    params = {"network_id": data["network_id"], "name": data["name"], "cidr": data["cidr"],
              "ip_version": int(data["ip_version"])}
    body = {"subnet": params}   

    _setup_subnet_parameters(params, data)

    subnet = OpenstackNetworkService.create_subnet(body).get("subnet")

    return subnet


def update_subnet(data):
    """
    Update a subnet
    """
    params = {"name": data["name"]}
    body = {"subnet": params}
    subnet_id = data.pop("subnet_id")

    _setup_subnet_parameters(params, data)

    # we should only send gateway_ip only when it's changed
    # because updating gateway_ip is prohibited
    # when the ip is used.
    # see bug 1227268
    if params.get("gateway_ip"):
        subnet = OpenstackNetworkService.show_subnet(subnet_id).get("subnet")
        if params["gateway_ip"] == subnet["gateway_ip"]:
            del params["gateway_ip"]

    subnet = OpenstackNetworkService.update_subnet(subnet_id, body).get("subnet")

    return subnet


def list_ports_by_instance(instance_id):
    """
    Fetch all the ports of a instance, used in Neutron
    """
    search_opts = {'device_id': instance_id}

    ports = OpenstackNetworkService.list_ports(**search_opts).get('ports')

    return ports


def get_port_range(rule):
    """
    Get a security group rule's port range
    """
    ip_proto = rule['ip_protocol']

    def _check_rule_template(port):
        rules_dict = getattr(settings, 'SECURITY_GROUP_RULES', {})
        if not rules_dict:
            return port
        templ_rule = list(filter(lambda rule: str(port) == rule['from_port']
                            and str(port) == rule['to_port']
                            and ip_proto == rule['ip_protocol'],
                            [rule for rule in rules_dict.values()]))
        if templ_rule:
            return '%(from_port)s (%(name)s)' % templ_rule[0]
        return port

    if rule['from_port'] and rule['from_port'] == rule['to_port']:
        return _check_rule_template(rule['from_port'])
    else:
        return ('%(from)s - %(to)s' % 
                {'from': _check_rule_template(rule['from_port']) or '',
                 'to': _check_rule_template(rule['to_port']) or ''})


