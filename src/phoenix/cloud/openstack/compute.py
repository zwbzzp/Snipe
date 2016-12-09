# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# Openstack API implementation
#
# 2016/1/25 lipeizhao: Init

import sys

from phoenix.cloud.openstack.client import ClientManager
from phoenix.cloud.utils import wrap_cloud_retry
from phoenix.common.proxy import SimpleProxy


def get_backend():
    """
    The backend is this module itself.
    """
    return sys.modules[__name__]

NOVA_CLI = SimpleProxy(lambda: ClientManager().nova_client)

# SERVERS = SimpleProxy(lambda: NOVA_CLI.servers)
# FLAVORS = SimpleProxy(lambda: NOVA_CLI.flavors)


###################


def get_server(server):
    """
    Get server by server object or server ID.
    """
    return NOVA_CLI.servers.get(server)


def get_server_by_name(name):
    """
    Get server by name.
    """
    return NOVA_CLI.servers.find(name=name)


def list_servers(detailed=True, search_opts=None, marker=None, limit=None,
                 sort_keys=None, sort_dirs=None):
    """
    List all servers.
    """
    return NOVA_CLI.servers.list(detailed=detailed,
                        search_opts=search_opts,
                        marker=marker,
                        limit=limit,
                        sort_keys=sort_keys,
                        sort_dirs=sort_dirs)


@wrap_cloud_retry(max_retries=3, retry_on_disconnect=True)
def add_ip_to_server(server, address):
    """
    Bind ip to server.
    """
    NOVA_CLI.servers.add_floating_ip(server, address)


@wrap_cloud_retry(max_retries=3, retry_on_disconnect=True)
def remove_ip_from_server(server, address):
    """
    Remove ip to server.
    """
    NOVA_CLI.servers.remove_floating_ip(server, address)
    

def get_server_console(server, console_type, console_sub_type=None):
    """
    Get a console for an instance. Type of console may include rdp, spice or vnc.
    """

    console_mapping = {'vnc': NOVA_CLI.servers.get_vnc_console,
                       'spice': NOVA_CLI.servers.get_spice_console,
                       'rdp': NOVA_CLI.servers.get_rdp_console}
    console = console_mapping.get(console_type, NOVA_CLI.servers.get_vnc_console)

    return console(server, console_sub_type)


def stop_server(server):
    """
    Stop the server.
    """
    NOVA_CLI.servers.stop(server)


def force_delete_server(server):
    """
    Force delete the server.
    """
    return NOVA_CLI.servers.force_delete(server)


def restore_server(server):
    """
    Restore soft-deleted server.
    """
    return NOVA_CLI.servers.restore(server)


def start_server(server):
    """
    Start the server.
    """
    NOVA_CLI.servers.start(server)


def pause_server(server):
    """
    Pause the server.
    """
    NOVA_CLI.servers.pause(server)


def unpause_server(server):
    """
    Unpause the server.
    """
    NOVA_CLI.servers.unpause(server)


def lock_server(server):
    """
    Lock the server.
    """
    NOVA_CLI.servers.lock(server)


def unlock_server(server):
    """
    Unlock the server.
    """
    NOVA_CLI.servers.unlock(server)

        
def suspend_server(server):
    """
    Suspend the server.
    """
    NOVA_CLI.servers.suspend(server)


def resume_server(server):
    """
    Resume the server.
    """
    NOVA_CLI.servers.resume(server)
    

def rescue_server(server, password=None, image=None):
    """
    Rescue the server.
    """
    NOVA_CLI.servers.rescue(server, password, image)


def unrescue_server(server):
    """
    Unrescue the server.
    """
    NOVA_CLI.servers.unrescue(server)


def shelve_server(server):
    """
    Shelve the server.
    """
    NOVA_CLI.servers.shelve(server)


def shelve_offload_server(server):
    """
    Remove a shelved instance from the compute node.
    """
    NOVA_CLI.servers.shelve_offload(server)


def unshelve_server(server):
    """
    Unshelve the server.
    """
    NOVA_CLI.servers.unshelve(server)


def get_server_ips(server):
    """
    Return IP Addresses associated with the server.
    """
    return NOVA_CLI.servers.ips(server)


def create_server(name, image, flavor, meta=None, files=None,
                  reservation_id=None, min_count=None,
                  max_count=None, security_groups=None, userdata=None,
                  key_name=None, availability_zone=None,
                  block_device_mapping=None, block_device_mapping_v2=None,
                  nics=None, scheduler_hints=None,
                  config_drive=None, disk_config=None, admin_pass=None, **kwargs):
    """
    Create (boot) a new server.
    """
    return NOVA_CLI.servers.create(name, image, flavor, meta, files,
                          reservation_id, min_count,
                          max_count, security_groups, userdata,
                          key_name, availability_zone,
                          block_device_mapping, block_device_mapping_v2,
                          nics, scheduler_hints,
                          config_drive, disk_config, admin_pass, **kwargs)


def update(server, name=None):
    """
    Update the name or the password for a server.
    """
    return NOVA_CLI.servers.update(server, name)


def delete_server(server):
    """
    delete the server.
    """
    NOVA_CLI.servers.delete(server)


def reboot_server(server, soft_reboot=True):
    """
    Reboot a server.
    """
    reboot_type = 'SOFT' if soft_reboot else 'HARD'
    NOVA_CLI.servers.reboot(server, reboot_type)


def rebuild_server(server, image):
    """
    Rebuild a server
    """
    return NOVA_CLI.servers.rebuild(server, image)


def migrate_server(server):
    """
    Migrate a server to a new host.
    """
    NOVA_CLI.servers.migrate(server)


def resize_server(server, flavor, disk_config=None, **kwargs):
    """
    Resize a server's resources.
    """
    NOVA_CLI.servers.resize(server, flavor, disk_config, **kwargs)


def confirm_resize_server(server):
    """
    Confirm that the resize worked, thus removing the original server.

    :param server: The :class:`Server` (or its ID) to share onto.
    """
    NOVA_CLI.servers.confirm_resize(server)


def revert_resize_server(server):
    """
    Revert a previous resize, switching back to the old server.

    :param server: The :class:`Server` (or its ID) to share onto.
    """
    NOVA_CLI.servers.revert_resize(server)


def create_image_from_server(server, image_name):
    """
    Snapshot a server.
    """
    return NOVA_CLI.servers.create_image(server,image_name)

    
def backup_server(server, backup_name, backup_type, rotation):
    """
    Backup a server instance.
    """
    NOVA_CLI.servers.backup(server, backup_name, backup_type, rotation)

    
def live_migrate_server(server, host, block_migration, disk_over_commit):
    """
    Migrates a running instance to a new machine.
    """
    return NOVA_CLI.servers.live_migrate(server, host, block_migration, disk_over_commit)


def reset_server_state(server, state='error'):
    """
    Reset the state of an instance to active or error.
    """
    NOVA_CLI.servers.reset_state(server, state)


def reset_server_network(server):
    """
    Reset network of an instance.
    """
    NOVA_CLI.servers.reset_network(server)


def add_security_group_to_server(server, security_group):
    """
    Add a Security Group to an instance
    """
    NOVA_CLI.servers.add_security_group(server, security_group)


def remove_security_group_to_server(server, security_group):
    """
    Remove a Security Group to an instance
    """
    NOVA_CLI.servers.remove_security_group(server, security_group)


def list_security_group_of_server(server):
    """
    List Security Group(s) of an instance
    """
    return NOVA_CLI.servers.list_security_group(server)


def evacuate_server(server, host=None, on_shared_storage=True):
    """
    Evacuate a server instance.
    """
    return NOVA_CLI.servers.evacuate(server, host, on_shared_storage)


def list_flavors(detailed=True, is_public=True, marker=None, limit=None):
    """
    Get a list of all flavors.
    """
    return NOVA_CLI.flavors.list(detailed, is_public, marker, limit)


def get_flavor(flavor):
    """
    Get a specific flavor by object or object id.
    """
    return NOVA_CLI.flavors.get(flavor)


def get_flavor_by_name(name):
    """
    Get a specific flavor by name.
    """
    return NOVA_CLI.flavors.find(name=name)


def delete_flavor(flavor):
    """
    Delete a specific flavor.
    """
    NOVA_CLI.flavors.delete(flavor)


def create_flavor(name, ram, vcpus, disk, flavorid="auto",
                  ephemeral=0, swap=0, rxtx_factor=1.0, is_public=True):
    """
    Create a flavor.
    """
    return NOVA_CLI.flavors.create(name, ram, vcpus, disk, flavorid,
                          ephemeral, swap, rxtx_factor, is_public)


def set_meta(server, metadata):
    """
    Set a servers metadata
    :param server: The :class:`Server` to add metadata to
    :param metadata: A dict of metadata to add to the server
    """
    return NOVA_CLI.servers.set_meta(server, metadata)


def delete_meta(server, keys):
    """
    Delete metadata from an server
    :param server: The :class:`Server` to add metadata to
    :param keys: A list of metadata keys to delete from the server
    """
    return NOVA_CLI.servers.delete_meta(server, keys)


def list_hosts(zone=None):
    """
    List All Hosts
    :param zone:
    :return:
    """
    return NOVA_CLI.hosts.list(zone=zone)


def list_hypervisors(detailed=True):
    """
    List All Hypervisors
    :param detailed:
    :return:
    """
    return NOVA_CLI.hypervisors.list(detailed=detailed)


def get_servers_of_hypervisor(hypervisor_match,servers=True):
    """
    Get a list server of matched hypervisor
    :param hypervisor_match: hypervirsor's host_name
    :param servers:
    :return:
    """
    return NOVA_CLI.hypervisors.search(hypervisor_match,servers)


def show_hypervisor(hypervisor):
    """
    Get a hypervisor detailed info
    :param hypervisor: hypervisor ID
    :return:
    """
    return NOVA_CLI.hypervisors.get(hypervisor)


def list_services(host=None,binary=None):
    """
    Get  services and status
    :param host:
    :param binary:
    :return:
    """
    return NOVA_CLI.services.list(host=host,binary=binary)


def enable_service(host, binary):
    """
    Enable service
    :param host:
    :param binary:
    :return:
    """
    return NOVA_CLI.services.enable(host,binary)


def disable_service(host, binary):
    """
    Disable service
    :param host:
    :param binary:
    :return:
    """
    return NOVA_CLI.services.disable(host, binary)
