# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# openstack client
#
# 2016/1/23 lipeizhao : Init

import threading
import functools
import logging

from keystoneclient.v2_0 import client as os_keystone_client
from novaclient import client as os_nova_client
from neutronclient.v2_0 import client as os_neutron_client
import glanceclient as os_glance_client
import swiftclient as os_swift_client

from phoenix.common.singleton import SingletonMixin
from phoenix.common import timeutils
import phoenix.config as cfg

LOG = logging.getLogger(__name__)

# openstack generic option
os_options = [
    cfg.StrOpt('username', default='demo',
               help='The user name for openstack access'),
    cfg.StrOpt('password', default='admin123',
               help='The password for openstack access'),
    cfg.StrOpt('tenant', default='demo',
               help='The tenant(project ID) of openstack'),
    cfg.StrOpt('auth_url', default='http://172.18.215.195:5000/v2.0',
               help='The authentication url'),
]
cfg.CONF.register_opts(os_options, group='openstack')

# openstack admin options
os_admin_options = [
    cfg.StrOpt('auth_url', default=''),
    cfg.StrOpt('tenant', default='admin'),
    cfg.StrOpt('username', default='admin'),
    cfg.StrOpt('password', default='admin123'),
]
cfg.CONF.register_opts(os_admin_options, group='openstack_admin')


def __keystone_authenticate(f):
        def wrapped(*args, **kwargs):
            try:
                result = f(*args, **kwargs)
            finally:
                keystone = args[0]
                if keystone.auth_ref is not None:
                    issued = keystone.auth_ref.issued
                    expires = keystone.auth_ref.expires
                    local_expires = timeutils.utcnow() + (expires - issued)
                    local_issued = timeutils.utcnow()
                    keystone.auth_ref['token']['issued_at'] = local_issued.isoformat()
                    keystone.auth_ref['token']['expires'] = local_expires.isoformat()
            return result
        return functools.update_wrapper(wrapped, f)

# monkey patch keystone client
os_keystone_client.Client.authenticate = __keystone_authenticate(
    os_keystone_client.Client.authenticate)


class ClientManager(SingletonMixin):

    _keystone_client = None
    _nova_client = None
    _glance_client = None
    _neutron_client = None
    _swift_client = None
    
    def __init__(self):
        self._username = cfg.CONF.openstack.username
        self._password = cfg.CONF.openstack.password
        self._tenant = cfg.CONF.openstack.tenant
        self._auth_url = cfg.CONF.openstack.auth_url
        
        self._keystone_lock = threading.Lock()
        self._nova_lock = threading.Lock()
        self._glance_lock = threading.Lock()
        self._neutron_lock = threading.Lock()
        self._swift_lock = threading.Lock()

        self._nova_api_version = '2'
        self._glance_api_version = '2'

    def __client_cache(f):
        """ Cloud client cache decorator
        :param f: factory function
        :return: factory function with cache support
        """
        f._client = None
        f._token = None

        def inner(*args, **kwargs):
            client_manager = args[0]
            if f._client is None or f._token != client_manager.token:
                f._client = f(*args, **kwargs)
                f._token = client_manager.token
                LOG.info('token of client %s expired, refreshed from openstack' % f.__name__)
            return f._client
        return functools.update_wrapper(inner, f)

    @property
    def keystone_client(self):
        if not self._keystone_client:
            with self._keystone_lock:
                if not self._keystone_client:
                    self._keystone_client = os_keystone_client.Client(
                        username=self._username, password=self._password,
                        tenant_name=self._tenant,
                        auth_url=self._auth_url)
        return self._keystone_client

    @property
    def token(self):
        return self.keystone_client.auth_token

    @property
    @__client_cache
    def nova_client(self):
        return os_nova_client.Client(version=self._nova_api_version,
                                     username=self._username,
                                     auth_token=self.keystone_client.auth_token,
                                     project_id=self._tenant,
                                     auth_url=self._auth_url)
    
    @property
    @__client_cache
    def neutron_client(self):
        endpoint = self.keystone_client.service_catalog.url_for(service_type='network')
        return os_neutron_client.Client(endpoint_url=endpoint,
                                        token=self.keystone_client.auth_token)
    
    @property
    @__client_cache
    def glance_client(self):
        endpoint = self.keystone_client.service_catalog.url_for(service_type='image')
        token = self._keystone_client.auth_token
        return os_glance_client.Client(version=self._glance_api_version,
                                       endpoint=endpoint,
                                       token=token)
    
    @property
    @__client_cache
    def swfit_client(self):
        return os_swift_client.Connection(
            preauthtoken=self.keystone_client.auth_token,
            authurl=self._auth_url)


class AdminClientManager(ClientManager):
    def __init__(self):
        if not cfg.CONF.openstack_admin.auth_url or \
                not cfg.CONF.openstack_admin.tenant or \
                not cfg.CONF.openstack_admin.username or \
                not cfg.CONF.openstack_admin.password:
            raise Exception('Can not find openstack admin account')

        self._username = cfg.CONF.openstack_admin.username
        self._password = cfg.CONF.openstack_admin.password
        self._tenant = cfg.CONF.openstack_admin.tenant
        self._auth_url = cfg.CONF.openstack_admin.auth_url

        self._keystone_lock = threading.Lock()
        self._nova_lock = threading.Lock()
        self._glance_lock = threading.Lock()
        self._neutron_lock = threading.Lock()
        self._swift_lock = threading.Lock()

        self._nova_api_version = '2'
        self._glance_api_version = '2'
