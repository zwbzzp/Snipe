# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# Network API
#
# 2016/1/23 lipeizhao: implementation

from phoenix.cloud import utils
from phoenix.cloud import CONF


_BACKEND_MAPPING = {'openstack': 'phoenix.cloud.openstack.network'}

IMPL = utils.CLOUDAPI.from_config(conf=CONF, backend_mapping=_BACKEND_MAPPING)


def is_neutron_network():
    """
    Determine whether the network is neutron 
    """
    return IMPL.is_neutron_network()


def list_networks(retrieve_all=True, **_params):
    """Fetches a list of all networks for a tenant."""
    return IMPL.list_networks(retrieve_all, **_params)


def get_network_by_name(name):
    """Fetches information of a certain network."""
    return IMPL.get_network_by_name(name)


def create_network(body=None):
    """Creates a new network."""
    return IMPL.create_network(body)


def update_network(network, body=None):
    """
    Update the specified network
    """
    return IMPL.update_network(network, body)


def show_network(network, **_params):
    """
    Fetches information of a certain network.
    """
    return IMPL.show_network(network, **_params)


def list_subnets(retrieve_all=True, **_params):
    """Fetches a list of all subnets for a tenant."""
    return IMPL.list_subnets(retrieve_all, **_params)


def delete_network(network):
    """Deletes the specified network."""
    return IMPL.delete_network(network)


def create_subnet(body=None):
    """Creates a new subnet."""
    return IMPL.create_subnet(body)


def update_subnet(subnet, body=None):
    """Updates a subnet."""
    return IMPL.update_subnet(subnet, body)


def delete_subnet(subnet):
    """Deletes the specified subnet."""
    return IMPL.delete_subnet(subnet)


def show_subnet(subnet, **_params):
    """Fetches information of a certain subnet."""
    return IMPL.show_subnet(subnet, **_params)


def list_ports(retrieve_all=True, **_params):
    """Fetches a list of all networks for a tenant."""
    return IMPL.list_ports(retrieve_all, **_params)


def create_port(body=None):
    """Creates a new port."""
    return IMPL.create_port(body)


def delete_port(port):
    """Deletes the specified port."""
    return IMPL.delete_port(port)


def update_port(port, body=None):
    """Updates a port."""
    return IMPL.update_port(port, body)


def list_routers(retrieve_all=True, **_params):
    """Fetches a list of all routers for a tenant."""
    return IMPL.list_routers(retrieve_all, **_params)


def create_router(body=None):
    """Creates a new router."""
    return IMPL.create_router(body)


def delete_router(router):
    """Deletes the specified router."""
    return IMPL.delete_router(router)


def show_router(router, **_params):
    """Fetches information of a certain router."""
    return IMPL.show_router(router, **_params)


def add_interface_router(router, body=None):
    """Adds an internal network interface to the specified router."""
    return IMPL.add_interface_router(router, body)


def remove_interface_router(router, body=None):
    """Removes an internal network interface from the specified router."""
    return IMPL.remove_interface_router(router, body)


def add_gateway_router(router, body=None):
    """Adds an external network gateway to the specified router."""
    return IMPL.add_gateway_router(router, body)


def remove_gateway_router(router):
    """Removes an external network gateway from the specified router."""
    return IMPL.remove_gateway_router(router)


def associate_floating_ip(server):
    """
    associate floating ip to vm
    """
    return IMPL.associate_floating_ip(server)


def disassociate_floating_ip(server):
    """
    disassociate floating ip from vm
    """
    return IMPL.disassociate_floating_ip(server)


def list_floatingips():
    """
    Fetches a list of all floating ips for a tenant.
    """
    return IMPL.list_floatingips()


def update_floatingip(floatingip, body=None):
    """
    Updates a floatingip.
    """
    return IMPL.update_floatingip(floatingip, body)


def add_floating_ip(server, address, fixed_address=None):
    """
    Add a floating IP to an instance
    """
    return IMPL.add_floating_ip(server, address, fixed_address)


def remove_floating_ip(server, address):
    """
    Remove a floating IP address [use in Nova-network]
    """
    return IMPL.remove_floating_ip(server, address)


def delete_floating_ip(floating_ip_id):
    """
    Delete (deallocate) a  floating IP for a tenant [use in Nova-network]
    :param floating_ip_id: The floating IP address to delete.
    """
    return IMPL.delete_floating_ip(floating_ip_id)


def list_floating_ip_pools():
    """
    Fetch a list of all floating ip pools
    """
    return IMPL.list_floating_ip_pools()


def allocate_floating_ip(pool):
    """
    Create (allocate) a  floating IP for a tenant
    :param pool: The floating IP pool from which allocate a floating ip;
                when use Nova-network, the pool is the pool's name;
                when use Neutron, the pool is a external network id 
    """
    return IMPL.allocate_floating_ip(pool)


def list_security_groups(**search_opts):
    """Fetches a list of all security groups for a tenant."""

    return IMPL.list_security_groups(**search_opts)


def create_security_group(name, desc):
    """Creates a new security group."""
    return IMPL.create_security_group(name, desc)


def delete_security_group(security_group_id):
    """Deletes the specified security group."""
    return IMPL.delete_security_group(security_group_id)


def update_security_group(sg_id, name, desc):
    """Updates a security group."""
    return IMPL.update_security_group(sg_id, name, desc)


def show_security_group(security_group_id):
    """Fetches information of a certain security group."""

    return IMPL.show_security_group(security_group_id)


def create_security_group_rule(parent_group_id, direction=None, ethertype=None,
                               ip_protocol=None, from_port=None, to_port=None,
                               cidr=None, group_id=None):
    """
    Creates a new security group rule.
    """
    return IMPL.create_security_group_rule(parent_group_id, direction, ethertype, \
           ip_protocol, from_port, to_port, cidr, group_id)


def delete_security_group_rule(rule):
    """Deletes the specified security group rule."""
    return IMPL.delete_security_group_rule(rule)