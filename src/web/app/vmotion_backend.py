# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# comment
#
# 16-8-06 qinjinghui : Init
# 16-8-22 chengkang  : update

from kazoo.client import KazooClient
import time
from abc import ABCMeta, abstractmethod
from functools import partial
import heapq
from oslo_config import cfg

from . import db
from .email import send_email
from .image.utils import with_app_context
from .vmotion.utils import evacuate_vms_to_active_hosts
from .models import HostInfo, Desktop, Parameter
from phoenix.cloud.admin import compute as OpenstackComputeService
import logging

LOG = logging.getLogger('vmotion')

class ZooKeeperApp(object):
    """
    We call the thing which we want to monitor a app,
    it must have a node and a handler at least, the node is a directory in ZooKeeper,
    the handler is a function which used to process monitoring changes, e.g. when a 
    host is down, the handler will be called.
    """
    __metaclass__ = ABCMeta

    def __init__(self, node):
        self.node = node
        self.lock = None

    def set_lock(self, lock):
        """
        Sometimes app's handler will be invoked within a thread or greenlet,
        so we need a lock to deal with the synchronization problem,
        The lock's type is determined by the KazooClient's handler, if we 
        can't be sure, just leave it alone.
        """
        self.lock = self.lock or lock

    @abstractmethod
    def handler(self, children):
        print('Children of node<"%s"> changed: %s' % (self.node, children))


class ZooKeeperWatcher(object):
    """
    We use a watcher to monitor an arbitrary number of apps, of course, these
    apps must be held by the same ZooKeeper server.
    """

    def __init__(self, hosts, apps):
        self.client = KazooClient(hosts=hosts)
        self.apps = apps

    def _lock_object(self):
        return self.client.handler.lock_object()

    def _add_watch(self):
        def watch(app, children):
            self.client.handler.spawn(app.handler, children)
            
        for app in self.apps:
            app.set_lock(self._lock_object())
            self.client.ensure_path(app.node)
            self.client.ChildrenWatch(path=app.node, func=partial(watch, app))

    def start(self, block=False):
        self.client.start()
        self._add_watch()

        if block:
            while True:
                time.sleep(3)


update_lock = None
deal_lock = None

def send_notification(nodes=[], evacuate_node=None, fail_dict={}):
    email = Parameter.query.filter_by(name="vmotion_notification_email").first()
    # refresh is important, otherwise we may read the cache data
    db.session.refresh(email)
    if not email:
        LOG.warning('Vmotion notification email is empty, cannot send notification')
    else:
        try:
            send_email(email.value, '云课室 - 系统报警', 'vmotion/email/notification', nodes=nodes, 
                        evacuate_node=evacuate_node, fail_dict=fail_dict)
        except Exception as ex:
            LOG.exception('[Vmotion]send system notification fail')

'''
def evacuate_vms_to_active_hosts(src_host_name, dest_host_list, vm_list=None):
    if not vm_list:
        temp_list = OpenstackComputeService.list_servers(search_opts={"host": src_host_name})
        vm_list = [vm for vm in temp_list if vm.status != 'ERROR' ]
        if not vm_list:
            LOG.warning('vm list empty')
            return

    flavor_dict = dict([(flavor.id, flavor) for flavor in OpenstackComputeService.list_flavors()])
    vm_flavor_dict = dict([(vm.id, flavor_dict[vm.flavor['id']]) for vm in vm_list])

    free_mem_heap = []
    for host in dest_host_list:
        # heapq is minimum heap, if we want to use a maximum heap, let the real value become a negative number
        heapq.heappush(free_mem_heap, (int(host.mem_used) - int(host.mem), host.host_name))

    fail_list = []
    for vm in vm_list:
        selected_host = heapq.heappop(free_mem_heap)
        free_mem, host_name = selected_host
        free_mem *= -1
        if free_mem < vm_flavor_dict[vm.id].ram:
            fail_list.append(vm)
            LOG.warning('[A]free_mem %s less than %s' % (free_mem, vm_flavor_dict[vm.id].ram))
            heapq.heappush(free_mem_heap, selected_host)
            continue
        else:
            desktop = Desktop.query.filter_by(vm_ref=vm.id).first()
            if not desktop:
                heapq.heappush(free_mem_heap, selected_host)
                continue
            else:
                if evacuate_desktop(desktop.vm_ref, host_name):
                    free_mem -= vm_flavor_dict[vm.id].ram
                    heapq.heappush(free_mem_heap, (free_mem * -1, host_name))
                else:
                    LOG.warning('[B]evacuate desktop fail')
                    fail_list.append(vm)
                    heapq.heappush(free_mem_heap, selected_host)

    return fail_list
'''     

def deal_with_nodes_changed(up_nodes=[], down_nodes=[], is_ext=True):

    net_field = 'external_network_state' if is_ext else 'management_network_state'
    with update_lock:
        for node in up_nodes:
            try:
                hostinfo = HostInfo.query.filter_by(host_name=node).first()
                if not hostinfo:
                    continue

                db.session.refresh(hostinfo)
                setattr(hostinfo, net_field, 'up')
                if hostinfo.management_network_state == "up" and hostinfo.external_network_state == "up" and \
                        hostinfo.service_state == "up":
                    hostinfo.host_status = 'up'
                elif hostinfo.host_status == 'down':
                        hostinfo.host_status = 'warning'
                db.session.add(hostinfo)
                db.session.commit()
            except Exception as ex:
                print(ex)

        for node in down_nodes:
            try:
                hostinfo = HostInfo.query.filter_by(host_name=node).first()
                if not hostinfo:
                    continue

                db.session.refresh(hostinfo)
                setattr(hostinfo, net_field, 'down')
                hostinfo.host_status = 'warning'

                if hostinfo.management_network_state == "down" and hostinfo.external_network_state == "down" and \
                        hostinfo.service_state == 'down':      
                    hostinfo.host_status = 'down'

                db.session.add(hostinfo)
                db.session.commit()
            except Exception as ex:
                LOG.exception(ex)

    if not down_nodes:
        return

    # wait 
    time.sleep(60)

    for node in down_nodes:
        try:
            hostinfo = HostInfo.query.filter_by(host_name=node).first()
            if not hostinfo:
                continue

            db.session.refresh(hostinfo)
            if hostinfo.external_network_state != "up" and hostinfo.management_network_state == 'up':
                LOG.info('node [%s] public network down' % node)
                send_notification(nodes=[hostinfo])
            if hostinfo.external_network_state == "up" and hostinfo.management_network_state != 'up':
                LOG.info('node [%s] management network down' % node)
                send_notification(nodes=[hostinfo])
            if hostinfo.external_network_state != 'up' and hostinfo.management_network_state != 'up':
                LOG.info('node [%s] public and management network down' % node)
                try:
                    # FIXME: wait for service_state(nova-compute) to be down and evacuate VMs to other nodes
                    # 这里等待的原因:一般管理网络down掉,计算服务的状态在短时间(小于5分钟)变为down,如果超过5分钟
                    # 计算服务状态还未变成down,说明有可能管理网络并未down,而是zookeeper agent挂掉了
                    max_retries, wait_time = 100, 3
                    while max_retries:
                        # here we need to refresh hostinfo's service_state,
                        # otherwise we may have read the cache data
                        db.session.refresh(hostinfo)
                        # 在我们等待服务状态改变时,可能网络已经恢复
                        if hostinfo.external_network_state == 'up' or hostinfo.management_network_state == 'up':
                            continue
                        if hostinfo.service_state == 'down':
                            break
                        time.sleep(wait_time)
                        max_retries -= 1
                    if max_retries <= 0:
                        LOG.warning('Wait for [%s] service to be down, but timeout after %ss' % (node, wait_time * max_retries))
                        continue

                    # this is the master switch of the auto evacuation
                    vmotion_auto_evacuation = Parameter.query.filter_by(name='vmotion_auto_evacuation').first()
                    db.session.refresh(vmotion_auto_evacuation)
                    if vmotion_auto_evacuation.value == 'off':
                        LOG.info('node [%s] down, vmotion_auto_evacuation is off' % node)
                        send_notification(nodes=[hostinfo])
                        continue

                    with update_lock:
                        db.session.refresh(hostinfo)
                        if hostinfo.auto_evacuation:
                            hostinfo.auto_evacuation = False
                            db.session.add(hostinfo)
                            db.session.commit()
                            LOG.info('node [%s] down, its auto_evacuation is true, begin evacuation' % node)
                            send_notification(evacuate_node=hostinfo)
                        else:
                            LOG.info('node [%s] down, its auto_evacuation is false' % node)
                            send_notification(nodes=[hostinfo])
                            continue

                    '''
                    Auto evacuation: First evacuate VMs to backup nodes, if backup nodes' capacity is not enough,
                                    then evacuate the reminded to other online nodes.
                    '''
                    
                    backup_host_list = HostInfo.query.filter_by(host_status="up", service_status="disabled").all()
                    online_host_list = HostInfo.query.filter_by(host_status="up", service_status="enabled").all()
                    if backup_host_list:
                        fail_vm_list = evacuate_vms_to_active_hosts(node, backup_host_list)
                        if fail_vm_list and online_host_list:
                            fail_vm_list = evacuate_vms_to_active_hosts(node, online_host_list, fail_vm_list)
                        if fail_vm_list:
                            fail_dict = { 'node': node, 'fail_list': []}
                            for vm in fail_vm_list:
                                desktop = Desktop.query.filter_by(vm_ref=vm.id).first()
                                if desktop:
                                    fail_dict['fail_list'].append({'name': desktop.name or vm.id,
                                                        'owner': desktop.owner.username if desktop.owner else '-'})
                            LOG.warning('node [%s] auto evacuation, fail desktop list: %s' % (node, fail_dict['fail_list']))
                            send_notification(fail_dict=fail_dict)
                    elif online_host_list:
                        fail_vm_list = evacuate_vms_to_active_hosts(node, online_host_list)
                        if fail_vm_list:
                            fail_dict = { 'node': node, 'fail_list': []}
                            for vm in fail_vm_list:
                                desktop = Desktop.query.filter_by(vm_ref=vm.id).first()
                                if desktop:
                                    fail_dict['fail_list'].append({'name': desktop.name or vm.id, 
                                                        'owner': desktop.owner.username if desktop.owner else '-'})
                            LOG.warning('node [%s] auto evacuation, fail desktop list: %s' % (node, fail_dict['fail_list']))
                            send_notification(fail_dict=fail_dict)
                    else:
                        fail_dict = { 'node': node, 'reason': '无其它节点可用来进行迁移'}
                        LOG.warning('node [%s] auto evacuation fail: %s' % (node, fail_dict['reason']))
                        send_notification(fail_dict=fail_dict)
                except Exception as ex:
                    LOG.exception('Node "%s" down, auto evacuation fail' % node)
        except Exception as ex:
            LOG.exception(ex)


class ExtNetApp(ZooKeeperApp):
    """
    The is our first app,
    we use it to monitor the compute nodes' public network.
    """

    def __init__(self, node):
        super(ExtNetApp, self).__init__(node)
        self.name = self.__class__.__name__
        self.children_cache = []

    @with_app_context
    def handler(self, children):
        try:       
            with self.lock:
                current_children_set = set(children)
                prev_children_set = set(self.children_cache)

                down_nodes = prev_children_set - current_children_set
                up_nodes = current_children_set - prev_children_set

                self.children_cache = children
                LOG.info('[%(name)s] children changed, current: %(children)s, down: %(down)s, up: %(up)s' % 
                            {'name': self.name, 'children': children, 'down': down_nodes, 'up': up_nodes})

            deal_with_nodes_changed(up_nodes, down_nodes)
        except Exception as ex:
            LOG.exception(ex)


class MgmtNetApp(ZooKeeperApp):
    """
    The is our second app,
    we use it to monitor the compute nodes' management network.
    """

    def __init__(self, node):
        super(MgmtNetApp, self).__init__(node)
        self.name = self.__class__.__name__
        self.children_cache = []

    @with_app_context
    def handler(self, children):
        try:       
            with self.lock:
                current_children_set = set(children)
                prev_children_set = set(self.children_cache)

                down_nodes = prev_children_set - current_children_set
                up_nodes = current_children_set - prev_children_set

                self.children_cache = children
                LOG.info('[%(name)s] children changed, current: %(children)s, down: %(down)s, up: %(up)s' % 
                            {'name': self.name, 'children': children, 'down': down_nodes, 'up': up_nodes})

            deal_with_nodes_changed(up_nodes, down_nodes, is_ext=False)
        except Exception as ex:
            LOG.exception(ex)


def service_monitor():
    while True:
        try:
            flavor_dict = {}
            flavor_list = OpenstackComputeService.list_flavors()
            for flavor in flavor_list:
                flavor_dict[flavor.id] = flavor

            vm_list = OpenstackComputeService.list_servers()
            running_vms_dict = {}
            for vm in vm_list:
                if vm.status == "ACTIVE":
                    host_name = vm.__dict__['OS-EXT-SRV-ATTR:host']
                    if host_name in running_vms_dict:
                        running_vms_dict[host_name] += 1
                    else:
                        running_vms_dict[host_name] = 1


            hypervisors_list = OpenstackComputeService.list_hypervisors(detailed=True)
            hostinfo_dict = {}
            for hypervisor in hypervisors_list:
                hostinfo_dict[hypervisor.hypervisor_hostname] = hypervisor

            services_list = OpenstackComputeService.list_services()
            for service in services_list:
                if service.binary == 'nova-compute':
                    hostinfo = HostInfo.query.filter_by(
                        host_name=service.host).first()
                    if not hostinfo:
                        continue

                    with update_lock:
                        db.session.refresh(hostinfo)
                        if hostinfo and (hostinfo.service_state != service.state or hostinfo.service_status != service.status):
                            hostinfo.service_state = service.state
                            hostinfo.service_status = service.status
                            if hostinfo.service_state != "up":
                                hostinfo.host_status = "warning"
                        if hostinfo and hostinfo.service_state == "down" and \
                                        hostinfo.management_network_state == "down" and hostinfo.external_network_state == "down":
                            hostinfo.host_status = "down"
                        if hostinfo and hostinfo.service_state == "up" and \
                                        hostinfo.management_network_state == "up" and hostinfo.external_network_state == "up":
                            hostinfo.host_status = "up"
                        hostinfo.vms = hostinfo_dict[service.host].running_vms
                        hostinfo.running_vms = running_vms_dict.get(service.host,0)
                        hostinfo.mem = hostinfo_dict[service.host].memory_mb
                        hostinfo.mem_used = hostinfo_dict[service.host].memory_mb_used
                        hostinfo.disk = hostinfo_dict[service.host].local_gb
                        hostinfo.disk_used = hostinfo_dict[service.host].local_gb_used
                        db.session.add(hostinfo)
                        db.session.commit()
        except:
            LOG.exception("List compute Service Exception")
        time.sleep(cfg.CONF.vmotion.service_state_refresh_interval)


def run():
    vmotion_conf = cfg.CONF.vmotion

    if vmotion_conf.enable:
        watcher = ZooKeeperWatcher(vmotion_conf.zookeeper, [ExtNetApp(vmotion_conf.ext_network_znode), MgmtNetApp(vmotion_conf.mgmt_network_znode)])
        global update_lock
        global deal_lock
        update_lock = watcher._lock_object()
        deal_lock = watcher._lock_object()
        watcher.start()
        service_monitor()
    else:
        print("Vmotion isn't enabled, quit..")




