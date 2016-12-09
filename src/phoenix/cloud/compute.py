# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# Compute API
#
# 2016/1/23 lipeizhao: implementation

from phoenix.cloud import utils
from phoenix.cloud import CONF


_BACKEND_MAPPING = {'openstack': 'phoenix.cloud.openstack.compute'}

IMPL = utils.CLOUDAPI.from_config(conf=CONF, backend_mapping=_BACKEND_MAPPING)


def get_server(server):
    """
    Get server.
    """
    return IMPL.get_server(server)


def get_server_by_name(name):
    """
    Get server by name.
    """
    return IMPL.get_server_by_name(name)


def list_servers(detailed=True, search_opts=None, marker=None, limit=None,
                 sort_keys=None, sort_dirs=None):
    """
    List all servers.
    """
    return IMPL.list_servers(detailed, search_opts, marker, limit,
                             sort_keys, sort_dirs)


def add_ip_to_server(server, address):
    """
    Bind ip to server.
    """
    IMPL.add_ip_to_server(server, address)


def remove_ip_from_server(server, address):
    """
    Remove ip to server.
    """
    IMPL.remove_ip_from_server(server, address)
    

def get_server_console(server, console_type, console_sub_type=None):
    """
    Get a console for an instance. Type of console may include rdp, spice or vnc.
    """
    return IMPL.get_server_console(server, console_type, console_sub_type)


def stop_server(server):
    """
    Stop the server.
    """
    IMPL.stop_server(server)


def force_delete_server(server):
    """
    Force delete the server.
    """
    return IMPL.force_delete_server(server)


def restore_server(server):
    """
    Restore soft-deleted server.
    """
    return IMPL.restore_server(server)


def start_server(server):
    """
    Start the server.
    """
    return IMPL.start_server(server)


def pause_server(server):
    """
    Pause the server.
    """
    return IMPL.pause_server(server)
    

def unpause_server(server):
    """
    Unpause the server.
    """
    return IMPL.unpause_server(server)


def lock_server(server):
    """
    Lock the server.
    """
    return IMPL.lock_server(server)


def unlock_server(server):
    """
    Unlock the server.
    """
    return IMPL.unlock_server(server)

        
def suspend_server(server):
    """
    Suspend the server.
    """
    return IMPL.suspend_server(server)


def resume_server(server):
    """
    Resume the server.
    """
    return IMPL.resume_server(server)
    

def rescue_server(server, password=None, image=None):
    """
    Rescue the server.
    """
    return IMPL.rescue_server(server, password, image)


def unrescue_server(server):
    """
    Unrescue the server.
    """
    return IMPL.unres


def shelve_server(server):
    """
    Shelve the server.
    """
    return IMPL.shelve_server(server)


def shelve_offload_server(server):
    """
    Remove a shelved instance from the compute node.
    """
    return IMPL.shelve_offload_server(server)


def unshelve_server(server):
    """
    Unshelve the server.
    """
    return IMPL.unshelve_server(server)


def get_server_ips(server):
    """
    Return IP Addresses associated with the server.
    """
    return IMPL.get_server_ips(server)


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
    return IMPL.create_server(name, image, flavor, meta, files,
                              reservation_id, min_count,
                              max_count, security_groups, userdata,
                              key_name, availability_zone,
                              block_device_mapping, block_device_mapping_v2,
                              nics, scheduler_hints,
                              config_drive, disk_config, admin_pass, **kwargs)


def update_server(server, name=None):
    """
    Update the name or the password for a server.
    """
    return IMPL.update_server(server, name)


def delete_server(server):
    """
    delete the server.
    """
    return IMPL.delete_server(server)


def reboot_server(server, soft_reboot=True):
    """
    Reboot a server.
    """
    return IMPL.reboot_server(server, soft_reboot)


def rebuild_server(server, image):
    """
    Rebuild a server
    """
    return IMPL.rebuild_server(server, image)


def migrate_server(server):
    """
    Migrate a server to a new host.
    """
    return IMPL.migrate_server(server)


def resize_server(server, flavor, disk_config=None, **kwargs):
    """
    Resize a server's resources.
    """
    return IMPL.resize_server(server, flavor, disk_config, **kwargs)


def confirm_resize_server(server):
    """
    Confirm that the resize worked, thus removing the original server.

    :param server: The :class:`Server` (or its ID) to share onto.
    """
    return IMPL.confirm_resize_server(server)


def revert_resize_server(server):
    """
    Revert a previous resize, switching back to the old server.

    :param server: The :class:`Server` (or its ID) to share onto.
    """
    return IMPL.revert_resize_server(server)


def create_image_from_server(server, image_name):
    """
    Snapshot a server.
    """
    return IMPL.create_image_from_server(server, image_name)

    
def backup_server(server, backup_name, backup_type, rotation):
    """
    Backup a server instance.
    """
    return IMPL.backup_server(server, backup_name, backup_type, rotation)

    
def live_migrate_server(server, host, block_migration, disk_over_commit):
    """
    Migrates a running instance to a new machine.
    """
    return IMPL.live_migrate_server(server, host, block_migration, disk_over_commit)


def reset_server_state(server, state='error'):
    """
    Reset the state of an instance to active or error.
    """
    return IMPL.reset_server_state(server, state)


def reset_server_network(server):
    """
    Reset network of an instance.
    """
    return IMPL.reset_server_network(server)


def add_security_group_to_server(server, security_group):
    """
    Add a Security Group to an instance
    """
    return IMPL.add_security_group_to_server(server, security_group)


def remove_security_group_to_server(server, security_group):
    """
    Remove a Security Group to an instance
    """
    return IMPL.remove_security_group_to_server(server, security_group)


def list_security_group_of_server(server):
    """
    List Security Group(s) of an instance
    """
    return IMPL.list_security_group_of_server(server)


def evacuate_server(server, host=None, on_shared_storage=True):
    """
    Evacuate a server instance.
    """
    return IMPL.evacuate_server(server, host, on_shared_storage)


def list_flavors(detailed=True, is_public=True, marker=None, limit=None):
    """
    Get a list of all flavors.
    """
    return IMPL.list_flavors(detailed, is_public, marker, limit)


def get_flavor(flavor):
    """
    Get a specific flavor by object or object id.
    """
    return IMPL.get_flavor(flavor)


def get_flavor_by_name(name):
    """
    Get a specific flavor by name.
    """
    return IMPL.get_flavor_by_name(name)


def delete_flavor(flavor):
    """
    Delete a specific flavor.
    """
    return IMPL.delete_flavor(flavor)


def create_flavor(name, ram, vcpus, disk, flavorid="auto",
                  ephemeral=0, swap=0, rxtx_factor=1.0, is_public=True):
    """
    Create a flavor.
    """
    return IMPL.create_flavor(name, ram, vcpus, disk, flavorid,
                              ephemeral, swap, rxtx_factor, is_public)


def set_meta(server, metadata):
    """
    Set a servers metadata
    :param server: The :class:`Server` to add metadata to
    :param metadata: A dict of metadata to add to the server
    """
    return IMPL.set_meta(server, metadata)


def delete_meta(server, keys):
    """
    Delete metadata from an server
    :param server: The :class:`Server` to add metadata to
    :param keys: A list of metadata keys to delete from the server
    """
    return IMPL.delete_meta(server, keys)


def list_hosts(zone=None):
    """
    List All Hosts
    :param zone:
    :return:
    """
    return IMPL.list_hosts(zone)


def list_hypervisors(detailed=True):
    """
    List All Hypervisors
    :param detailed:
    :return:
    """
    return IMPL.list_hypervisors(detailed=detailed)


def get_servers_of_hypervisor(hypervisor_match,servers=True):
    """
    Get a list server of matched hypervisor
    :param hypervisor_match: hypervirsor's host_name
    :param servers:
    :return:
    """
    return IMPL.get_servers_of_hypervisor(hypervisor_match,servers)


def show_hypervisor(hypervisor):
    """
    Get a hypervisor detailed info
    :param hypervisor: hypervisor ID
    :return:
    """
    return IMPL.show_hypervisor(hypervisor)


def list_services(host=None,binary=None):
    """
    Get  services and status
    :param host:
    :param binary:
    :return:
    """
    return IMPL.list_services(host=host,binary=binary)


def enable_service(host, binary):
    """
    Enable service
    :param host:
    :param binary:
    :return:
    """
    return IMPL.enable_service(host,binary)


def disable_service(host, binary):
    """
    Disable service
    :param host:
    :param binary:
    :return:
    """
    return IMPL.disable_service(host, binary)
