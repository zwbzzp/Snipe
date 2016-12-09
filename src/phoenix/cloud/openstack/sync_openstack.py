# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# comment
#
# 4/19/16 bitson : Init

import os
import sys
import re

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))


import threading
import time
import logging

from phoenix.cloud.openstack.client import ClientManager
from phoenix.common.proxy import SimpleProxy
from phoenix.common.singleton import SingletonMixin

from phoenix import db
from phoenix.db.models import FloatingIp

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


class LocalFloatingIpManager(SingletonMixin):
    """Local floating ip manager."""

    # _stop_flag = False

    # def start_sync(self):
    #     LOG.info('Start local floating ip table refreshing thread')
    #     self.refresh_thread = threading.Thread(target=self.loop_refresh)
    #     self.refresh_thread.start()

    # def stop_sync(self):
    #     self._stop_flag = True

    def allocate_ip(self, external_net_id):
        if NEUTRON_CLI:
            ip = db.allocate_floating_ip(external_net_id)
            if not ip:
                body = {
                    'floatingip': {'floating_network_id': external_net_id}
                }
                result = NEUTRON_CLI.create_floatingip(body)
                new_floating_ip = result['floatingip']
                floating_ip_id = new_floating_ip['id']
                floating_ip_address = new_floating_ip['floating_ip_address']

                # add to floating ip table
                new_ip = FloatingIp()
                new_ip.ip_address = new_floating_ip['floating_ip_address']
                new_ip.external_network_id = new_floating_ip['floating_network_id']
                new_ip.ref_id = new_floating_ip['id']
                new_ip.status = FloatingIp.IP_STATUS.ACTIVE
                db.create_floating_ip(new_ip)
            else:
                floating_ip_id = ip.ref_id
                floating_ip_address = ip.ip_address
            return {'address': floating_ip_address,
                    'id': floating_ip_id}
        else:
            ip = db.allocate_floating_ip(external_net_id)
            if not ip:
                new_floating_ip = NOVA_CLI.floating_ips.create()
                new_ip = FloatingIp()
                new_ip.ip_address = new_floating_ip.ip
                new_ip.external_network_id = new_floating_ip.pool
                new_ip.ref_id = new_floating_ip.id
                new_ip.status = FloatingIp.IP_STATUS.ACTIVE
                db.create_floating_ip(new_ip)

                floating_ip_id = new_floating_ip.id
                floating_ip_address = new_floating_ip.ip
            else:
                floating_ip_id = ip.ref_id
                floating_ip_address = ip.ip_address
            return {'address': floating_ip_address,
                    'id': floating_ip_id}

    def reclaim_ip(self, ip):
        db.reclaim_floating_ip(ip)

    # def loop_refresh(self, frequency=10):
    #     while not self._stop_flag:
    #         self.refresh()
    #         time.sleep(frequency)

    def refresh(self):
        if NEUTRON_CLI:
            db.delete_all_floating_ip()
            server_ips = NEUTRON_CLI.list_floatingips()
            for ip in server_ips['floatingips']:
                new_ip = FloatingIp()
                new_ip.ip_address = ip['floating_ip_address']
                new_ip.external_network_id = ip['floating_network_id']
                new_ip.ref_id = ip['id']
                new_ip.status = ip['status'].lower()
                db.create_floating_ip(new_ip)

            # server_ips_dict = {}
            # server_ips = NEUTRON_CLI.list_floatingips()
            # for ip in server_ips['floatingips']:
            #     server_ips_dict[ip['floating_ip_address']] = ip
            #
            # local_ips_dict = {}
            # local_ips = db.get_all_floating_ips()
            # for ip in local_ips:
            #     local_ips_dict[ip.ip_address] = ip
            #
            # # remove not ip in server
            # for ip in local_ips:
            #     if not server_ips_dict.get(ip.ip_address, None):
            #         db.delete_floating_ip(ip.id)
            #
            # # add ip new in server
            # for ip in server_ips['floatingips']:
            #     if not local_ips_dict.get(ip['floating_ip_address'], None):
            #         new_ip = FloatingIp()
            #         new_ip.ip_address = ip['floating_ip_address']
            #         new_ip.external_network_id = ip['floating_network_id']
            #         new_ip.ref_id = ip['id']
            #         new_ip.status = ip['status'].lower()
            #         db.create_floating_ip(new_ip)
        else:
            db.delete_all_floating_ip()
            server_ips = NOVA_CLI.floating_ips.findall()
            for ip in server_ips:
                new_ip = FloatingIp()
                new_ip.ip_address = ip.ip
                new_ip.external_network_id = ip.pool
                new_ip.ref_id = ip.id
                new_ip.status = 'active' if ip.fixed_ip else 'down'
                db.create_floating_ip(new_ip)


    def clean(self):
        db.delete_all_floating_ip()

floating_ip_manager = LocalFloatingIpManager()

# if __name__ == '__main__':
#     floating_ip_manager.clean()
#     floating_ip_manager.start_sync()
