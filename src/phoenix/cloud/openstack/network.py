# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# Openstack API implementation
#
# 2016/1/25 lipeizhao: Init

import sys
import logging


from phoenix.cloud.openstack.client import ClientManager
from phoenix.cloud.utils import wrap_cloud_retry
from phoenix.common.proxy import SimpleProxy
from phoenix.cloud.openstack.sync_openstack import floating_ip_manager

LOG = logging.getLogger(__name__)

# check if neutron is supported
NEUTRON_CLI = None
KEYSTONE_CLI = SimpleProxy(lambda: ClientManager().keystone_client)
if KEYSTONE_CLI.service_catalog.get_endpoints(service_type='network'):
    NEUTRON_CLI = SimpleProxy(lambda: ClientManager().neutron_client)

NOVA_CLI = SimpleProxy(lambda: ClientManager().nova_client)

# get resource managers
# SERVERS = SimpleProxy(lambda: NOVA_CLI.servers)
# FLOATING_IPS = SimpleProxy(lambda: NOVA_CLI.floating_ips)
# FLOATING_IP_POOLS = SimpleProxy(lambda: NOVA_CLI.floating_ip_pools)
# SECURITY_GROUPS = SimpleProxy(lambda: NOVA_CLI.security_groups)
# SECURITY_GROUP_RULES = SimpleProxy(lambda: NOVA_CLI.security_group_rules)


def get_backend():
    """
    The backend is this module itself.
    """
    return sys.modules[__name__]

###################

def is_neutron_network():
    """
    Determine whether the network is neutron 
    """
    return NEUTRON_CLI is not None


def list_networks(retrieve_all=True, **_params):
    """
    Fetches a list of all networks for a tenant.
    """
    if NEUTRON_CLI is not None:
        return NEUTRON_CLI.list_networks(retrieve_all, **_params)
    return NOVA_CLI.networks.list()


def get_network_by_name(name):
    """Fetches information of a certain network."""
    networks = NEUTRON_CLI.list_networks()['networks']
    for net in networks:
        if net['name'] == name:
            return net
    return None


def create_network(body=None):
    """
    Creates a new network.
    """
    return NEUTRON_CLI.create_network(body)


def delete_network(network):
    """Deletes the specified network."""
    return NEUTRON_CLI.delete_network(network)


def update_network(network, body=None):
    """
    Update the specified network
    """
    return NEUTRON_CLI.update_network(network, body)


def show_network(network, **_params):
    """
    Fetches information of a certain network.
    """
    return NEUTRON_CLI.show_network(network, **_params)


def list_subnets(retrieve_all=True, **_params):
    """
    Fetches a list of all subnets for a tenant.
    """
    return NEUTRON_CLI.list_subnets(retrieve_all, **_params)


def create_subnet(body=None):
    """Creates a new subnet."""
    return NEUTRON_CLI.create_subnet(body)


def update_subnet(subnet, body=None):
    """Updates a subnet."""
    return NEUTRON_CLI.update_subnet(subnet, body)


def delete_subnet(subnet):
    """Deletes the specified subnet."""
    return NEUTRON_CLI.delete_subnet(subnet)


def show_subnet(subnet, **_params):
    """Fetches information of a certain subnet."""
    return NEUTRON_CLI.show_subnet(subnet, **_params)


def list_ports(retrieve_all=True, **_params):
    """Fetches a list of all networks for a tenant."""
    return NEUTRON_CLI.list_ports(retrieve_all, **_params)


def list_routers(retrieve_all=True, **_params):
    """Fetches a list of all routers for a tenant."""
    return NEUTRON_CLI.list_routers(retrieve_all, **_params)

def create_router(body=None):
    """Creates a new router."""
    return NEUTRON_CLI.create_router(body)


def delete_router(router):
    """Deletes the specified router."""
    return NEUTRON_CLI.delete_router(router)


def show_router(router, **_params):
    """Fetches information of a certain router."""
    return NEUTRON_CLI.show_router(router, **_params)


def create_port(body=None):
    """Creates a new port."""
    return NEUTRON_CLI.create_port(body)


def delete_port(port):
    """Deletes the specified port."""
    return NEUTRON_CLI.delete_port(port)


def update_port(port, body=None):
    """Updates a port."""
    return NEUTRON_CLI.update_port(port, body)


def add_interface_router(router, body=None):
    """Adds an internal network interface to the specified router."""
    return NEUTRON_CLI.add_interface_router(router, body)


def remove_interface_router(router, body=None):
    """Removes an internal network interface from the specified router."""
    return NEUTRON_CLI.remove_interface_router(router, body)


def add_gateway_router(router, body=None):
    """Adds an external network gateway to the specified router."""
    return NEUTRON_CLI.add_gateway_router(router, body)


def remove_gateway_router(router):
    """Removes an external network gateway from the specified router."""
    return NEUTRON_CLI.remove_gateway_router(router)


def get_vm_net_port_id(server):
    """
    get vm's port id in the private network that the vm is associate with,
    help function of associate floating ip
    """
    vm = NOVA_CLI.servers.get(server)
    private_net_name = None
    if vm:
        port_params = {'device_id': vm.id}
        ports = NEUTRON_CLI.list_ports(**port_params)
        port = ports['ports'][0] if ports['ports'] else None
        return port['id']
    return None


def get_vm_external_net_id(server):
    """get vm's external network id. help function of associate floating ip"""
    vm = NOVA_CLI.servers.get(server)
    private_net_name = None
    if vm:
        # get private network
        vm_nets = vm.networks

        private_net_name = list(vm_nets.keys())[0]

        # judge if vm already associate with a floating ip
        # TODO: should use a more robust method to judge if the vm already had a floating ip
        if len(vm_nets[private_net_name]) >= 2:
            LOG.warn('server %s already associated with floating ip' % vm.id)
            return None

        # get the private network of the vm
        private_nets = NEUTRON_CLI.list_networks(**{'name': private_net_name})
        private_net = private_nets['networks'][0] if private_nets['networks'] else None
        if not private_net:
            LOG.warn('server %s did not connect with private network' % vm.id)
            return None

        # get router interface port of the private network
        port_params = {
            'network_id': private_net['id'],
            'device_owner': 'network:router_interface'
        }
        ports = NEUTRON_CLI.list_ports(**port_params)
        port = ports['ports'][0] if ports['ports'] else None
        if not port:
            LOG.warn('server %s with private network %s did not connect with a router' %
                     (vm.id, private_net['id']))
        device_id = port['device_id']

        # get router by device id
        router_params = {
            'id': device_id
        }
        routers = NEUTRON_CLI.list_routers(**router_params)
        router = routers['routers'][0] if routers['routers'] else None

        # get router's external network id
        ext_net_id = router['external_gateway_info']['network_id']
        return ext_net_id

    return None


# nova-network and neutron support for floating ip

def __associate_floating_ip_nova_network(server):
    """
    associate floating ip with server in nova network
    """
    vm = NOVA_CLI.servers.get(server)
    network_name = 'nova'
    ip = floating_ip_manager.allocate_ip(network_name)
    NOVA_CLI.servers.add_floating_ip(server, ip['address'])
    return ip['address']


    # floating_ips = NOVA_CLI.floating_ips.findall(**{'fixed_ip': None})
    # if not floating_ips:
    #     floating_ip = NOVA_CLI.floating_ips.create().ip
    # else:
    #     floating_ip = floating_ips[0].ip if floating_ips else None
    #
    # NOVA_CLI.servers.add_floating_ip(server, floating_ip)
    # return floating_ip


def __disassociate_floating_ip_nova_network(server):
    """
    disassociate floating ip with server in nova network
    """
    vm = NOVA_CLI.servers.get(server)
    addresses = vm.addresses if vm.addresses else None
    if addresses:
        net_name = list(addresses.keys())[0]
        net_addresses = addresses[net_name]

        floating_ip = None
        for addr in net_addresses:
            if addr['OS-EXT-IPS:type'] == 'floating':
                floating_ip = addr['addr']
                break

        if floating_ip:
            NOVA_CLI.servers.remove_floating_ip(vm.id, floating_ip)
            floating_ip_manager.reclaim_ip(floating_ip)


def __associate_floating_ip_neutron(server):
    """
    associate floating ip to vm in neutron
    """
    external_net_id = get_vm_external_net_id(server)
    if not external_net_id:
        return None

    ip = floating_ip_manager.allocate_ip(external_net_id)
    ip_address = ip['address']
    ip_id = ip['id']
    update_dict = {}
    update_dict['port_id'] = get_vm_net_port_id(server)
    try:
        NEUTRON_CLI.update_floatingip(ip_id, {'floatingip': update_dict})
    except:
        floating_ip_manager.reclaim_ip(ip_address)
        raise
    return ip_address


def __disassociate_floating_ip_neutron(server):
    """
    disassociate floating ip from vm in neutron
    """
    vm = NOVA_CLI.servers.get(server)
    if vm:
        # get private network
        vm_nets = vm.networks

        private_net_name = list(vm_nets.keys())[0]
        private_net = vm_nets[private_net_name]

        # judge if the vm has associated with a floating ip
        # TODO: should use another method to judge if the vm has associated with a floating ip
        if len(private_net) == 1:
            return None

        floating_ip = private_net[len(private_net)-1]
        floating_ips = NEUTRON_CLI.list_floatingips(**{'floating_ip_address': floating_ip,
                                                       'status': 'ACTIVE'})
        ip = floating_ips['floatingips'][0] if floating_ips else None

        # update manager information
        floating_ip_manager.reclaim_ip(ip['floating_ip_address'])
        update_dict = {}
        update_dict['port_id'] = None
        NEUTRON_CLI.update_floatingip(ip['id'],
                                         {'floatingip': update_dict})


def associate_floating_ip(server):
    return \
        __associate_floating_ip_neutron(server) if NEUTRON_CLI \
            else __associate_floating_ip_nova_network(server)


def disassociate_floating_ip(server):
    return \
        __disassociate_floating_ip_neutron(server) if NEUTRON_CLI \
            else __disassociate_floating_ip_nova_network(server)


def list_floatingips():
    """
    Fetches a list of all floating ips for a tenant.
    """
    return NOVA_CLI.floating_ips.list()


def update_floatingip(floatingip, body=None):
    """
    Updates a floatingip [use in Neutron]
    """
    return NEUTRON_CLI.update_floatingip(floatingip, body)


def add_floating_ip(server, address, fixed_address=None):
    """
    Add a floating IP to an instance [use in Nova-network]
    """
    return NOVA_CLI.servers.add_floating_ip(server, address, fixed_address)


def remove_floating_ip(server, address):
    """
    Remove a floating IP address [use in Nova-network]
    """
    return NOVA_CLI.servers.remove_floating_ip(server, address)


def __delete_floating_ip_nova_network(floating_ip_id):
    """
    Delete (deallocate) a  floating IP for a tenant [use in Nova-network]
    :param floating_ip_id: The floating IP address to delete.
    """
    return NOVA_CLI.floating_ips.delete(floating_ip_id)


def __delete_floating_ip_neutron(floating_ip_id):
    """Deletes the specified floatingip."""
    return NEUTRON_CLI.delete_floatingip(floating_ip_id)


def delete_floating_ip(floating_ip_id):
    """
    Delete (deallocate) a  floating IP for a tenant [use in Nova-network]
    :param floating_ip_id: The floating IP address to delete.
    """
    return __delete_floating_ip_neutron(floating_ip_id) if NEUTRON_CLI \
            else __delete_floating_ip_nova_network(floating_ip_id)


def list_floating_ip_pools():
    """
    Fetch a list of all floating ip pools
    """
    return NOVA_CLI.floating_ip_pools.list()


def __allocate_floating_ip_nova_network(pool):
    """
    Create (allocate) a  floating IP for a tenant [use in Nova-network]
    """
    fip = NOVA_CLI.floating_ips.create(pool)
    return {'id': fip.id, 'ip': fip.ip, 'pool': fip.pool}


def __allocate_floating_ip_neutron(pool):
    """
    Create (allocate) a  floating IP for a tenant [use in Neutron]
    """
    body = {'floatingip': {'floating_network_id': pool}}
    fip = NEUTRON_CLI.create_floatingip(body).get('floatingip')
    return {'id': fip['id'], 'ip': fip['floating_ip_address'], 'pool': fip['floating_network_id']}


def allocate_floating_ip(pool):
    """
    Create (allocate) a  floating IP for a tenant
    :param pool: The floating IP pool from which allocate a floating ip;
                when use Nova-network, the pool is the pool's name;
                when use Neutron, the pool is a external network id 
    """
    return __allocate_floating_ip_neutron(pool) if is_neutron_network \
            else __allocate_floating_ip_nova_network(pool)


def __list_security_groups_nova_network(**search_opts):
    """
    Get a list of all security_groups

    :rtype: list of :class:`SecurityGroup`
    """
    sg_list = []
    for sg in NOVA_CLI.security_groups.list(search_opts):
        sg_dict = {}
        sg_dict['id'] = sg.id
        sg_dict['name'] = sg.name
        sg_dict['description'] = sg.description
        sg_dict['tenant_id'] = sg.tenant_id
        sg_dict['rules'] = sg.rules
        sg_list.append(sg_dict)

    return sg_list


def __set_secgroup_dict_neutron(sg_dict, secgroup, sg_name_dict=None):
    """
    Use neutron's secgroup data to fill our secgroup dict

    :param sg_dict: the dict we want to fill with data
    param secgroup: the neutron's secgroup dict data
    sg_name_dict: a dict which contain secgroup's id and name
    """
    if sg_name_dict is None:
        sg_name_dict = {secgroup['id']: secgroup['name']}

    __attrs = ['id', 'name', 'description', 'tenant_id']
    for __attr in __attrs:
        sg_dict[__attr] = secgroup.get(__attr)

    sg_dict['rules'] = []
    for sgr in secgroup['security_group_rules']:
        remote_ip_prefix = sgr.get('remote_ip_prefix')
        remote_group_id = sgr.get('remote_group_id')
        ethertype = sgr.get('ethertype')

        rule = {
            'id': sgr['id'],
            'parent_group_id': sgr['security_group_id'],
            'direction': sgr['direction'],
            'ethertype': ethertype,
            'ip_protocol': sgr['protocol'] or '',
            'from_port': sgr['port_range_min'],
            'to_port': sgr['port_range_max']
        }
        if not remote_ip_prefix and not remote_group_id:
            if ethertype == 'IPv6':
                remote_ip_prefix = '::/0'
            else:
                remote_ip_prefix = '0.0.0.0/0'

        rule['ip_range'] = {'cidr': remote_ip_prefix} if remote_ip_prefix else {}
        group = None
        if remote_group_id:
            group = sg_name_dict.get(remote_group_id, remote_group_id[:13])
        rule['group'] = {'name': group} if group else {}
        sg_dict['rules'].append(rule)


def __list_security_groups_neutron(retrieve_all=True, **_params):
    """Fetches a list of all security groups for a tenant."""
    sg_list = []
    for sg in NEUTRON_CLI.list_security_groups(retrieve_all, **_params).get('security_groups'):
        sg_dict = {}
        __set_secgroup_dict_neutron(sg_dict, sg)
        sg_list.append(sg_dict)

    return sg_list


def list_security_groups(**search_opts):
    """Fetches a list of all security groups for a tenant."""

    return __list_security_groups_neutron(**search_opts) if NEUTRON_CLI else \
        __list_security_groups_nova_network(**search_opts)


def __create_security_group_nova_network(name, desc):
    """
    Create a security group

    :param name: name for the security group to create
    param desc: description of the security group
    :rtype: the security group object
    """

    return NOVA_CLI.security_groups.create(name, desc)


def __create_security_group_neutron(name, desc):
    """Creates a new security group."""
    body = {'security_group': {'name': name, 'description': desc}}

    return NEUTRON_CLI.create_security_group(body)


def create_security_group(name, desc):
    """Creates a new security group."""
    return __create_security_group_neutron(name, desc) if NEUTRON_CLI else \
        __create_security_group_nova_network(name, desc)


def __delete_security_group_nova_network(security_group_id):
    """
    Delete a security group

    :param security_group_id: The security group id to delete
    :rtype: None
    """
    return NOVA_CLI.security_groups.delete(security_group_id)


def __delete_security_group_neutron(security_group_id):
    """Deletes the specified security group."""

    return NEUTRON_CLI.delete_security_group(security_group_id)


def delete_security_group(security_group_id):
    """Deletes the specified security group."""
    return __delete_security_group_neutron(security_group_id) if NEUTRON_CLI else \
        __delete_security_group_nova_network(security_group_id)


def __update_security_group_nova_network(sg_id, name, desc):
    """
    Update a security group

    :param sg_id: The security group id to update
    :param name: name for the security group to update
    :param desc: description for the security group to update
    :rtype: the security group object
    """
    return NOVA_CLI.security_groups.update(sg_id, name, desc)


def __update_security_group_neutron(sg_id, name, desc):
    """Updates a security group."""
    body = {'security_group': {'name': name, 'description': desc}}

    return NEUTRON_CLI.update_security_group(sg_id, body)


def update_security_group(sg_id, name, desc):
    """Updates a security group."""
    return __update_security_group_neutron(sg_id, name, desc) if NEUTRON_CLI else \
        __update_security_group_nova_network(sg_id, name, desc)


def __show_security_group_nova_network(security_group_id):
    """
    Get a security group

    :param group_id: The security group to get by ID
    :rtype: :class:`SecurityGroup`
    """
    secgroup = NOVA_CLI.security_groups.get(security_group_id)
    sg_dict = {}
    __attrs = ['id', 'name', 'description', 'tenant_id', 'rules']
    for __attr in __attrs:
        sg_dict[__attr] = getattr(secgroup, __attr, None)
    for rule in sg_dict['rules']:
        rule['direction'] = 'ingress'
        rule['ethertype'] = None

    return sg_dict


def __show_security_group_neutron(security_group_id):
    """Fetches information of a certain security group."""
    secgroup = NEUTRON_CLI.show_security_group(security_group_id).get('security_group')

    def _sg_name_dict(rules):
        """Create a mapping dict from secgroup id to its name."""
        related_ids = set([security_group_id])
        related_ids |= set(filter(None, [ r['remote_group_id'] for r in rules]))
        relate_sgs = NEUTRON_CLI.list_security_groups(id=related_ids, fields=['id', 'name']).get('security_groups')
        return dict((sg['id'], sg['name']) for sg in relate_sgs)
    sg_name_dict = _sg_name_dict(secgroup['security_group_rules'])

    sg_dict = {}
    __set_secgroup_dict_neutron(sg_dict, secgroup, sg_name_dict)

    return sg_dict


def show_security_group(security_group_id):
    """Fetches information of a certain security group."""

    return __show_security_group_neutron(security_group_id) if NEUTRON_CLI else \
        __show_security_group_nova_network(security_group_id)


def __create_secgroup_rule_nova_network(parent_group_id, direction=None, ethertype=None,
                                        ip_protocol=None, from_port=None, to_port=None,
                                        cidr=None, group_id=None):
    """
    Create a security group rule
    """

    # Nova Security Group API does not use direction and ethertype fields.
    return NOVA_CLI.security_group_rules.create(parent_group_id, ip_protocol, from_port, to_port, cidr, group_id)


def __create_secgroup_rule_neutron(parent_group_id, direction=None, ethertype=None,
                                   ip_protocol=None, from_port=None, to_port=None,
                                   cidr=None, group_id=None):
    """Creates a new security group rule."""
    cidr = cidr or None
    from_port = from_port if (from_port and from_port >= 0) else None
    to_port = to_port if (to_port and to_port >= 0) else None
    ip_protocol = None if (isinstance(ip_protocol, int) and ip_protocol < 0) else ip_protocol

    body = {'security_group_rule':
                {'security_group_id': parent_group_id,
                 'direction': direction,
                 'ethertype': ethertype,
                 'protocol': ip_protocol,
                 'port_range_min': from_port,
                 'port_range_max': to_port,
                 'remote_ip_prefix': cidr,
                 'remote_group_id': group_id}}
    return NEUTRON_CLI.create_security_group_rule(body)


def create_security_group_rule(parent_group_id, direction=None, ethertype=None,
                               ip_protocol=None, from_port=None, to_port=None,
                               cidr=None, group_id=None):
    """Creates a new security group rule."""
    return __create_secgroup_rule_neutron(parent_group_id, direction, ethertype, ip_protocol, from_port, to_port, \
           cidr, group_id) if NEUTRON_CLI else __create_secgroup_rule_nova_network(parent_group_id,  \
           direction, ethertype, ip_protocol, from_port, to_port, cidr, group_id)


def __delete_secgroup_rule_nova_network(rule):
    """
    Delete a security group rule

    :param rule: The security group rule to delete (ID or Class)
    """
    return NOVA_CLI.security_group_rules.delete(rule)


def __delete_secgroup_rule_neutron(rule):
    """Deletes the specified security group rule."""
    return NEUTRON_CLI.delete_security_group_rule(rule)


def delete_security_group_rule(rule):
    """Deletes the specified security group rule."""
    return __delete_secgroup_rule_neutron(rule) if NEUTRON_CLI else \
        __delete_secgroup_rule_nova_network(rule)









