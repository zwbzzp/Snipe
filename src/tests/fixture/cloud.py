import fixtures
import time

from phoenix.cloud import compute
from phoenix.cloud import image
from phoenix.cloud import network


class ServerEnv(fixtures.Fixture):
    """
    Create some servers for testing purpose.
    """
    test_image_name = 'win7'
    test_flavor_name = 'm1.large'
    time_out = 120

    test_network_suffix = 'private'
    test_network_name = 'test_network_private'

    def __init__(self, suffix):
        self.suffix = suffix

    def _setUp(self):
        image_get = image.get_image_by_name(self.test_image_name)
        flavor_get = compute.get_flavor_by_name(self.test_flavor_name)
        network_get = network.get_network_by_name(self.test_network_name)
        nics = [{"net-id": network_get['id']}]
        name = 'test_server_' + self.suffix
        self.test_server_op = compute.create_server(name=name,
                                                    image=image_get,
                                                    flavor=flavor_get,
                                                    nics=nics)

        time_out = 120
        time_pass = 0
        while time_pass < time_out:
            server_get = compute.get_server(self.test_server_op.id)
            if server_get.status == 'ACTIVE':
                break
            time_pass += 5
            time.sleep(5)


class PrivateNetworkEnv(fixtures.Fixture):
    """
    Create networking enviroment
    """
    subnet_name = 'test_subnet'
    cidr = '192.168.1.0/24'
    ip_version = 4
    gateway_ip = '192.168.1.1'
    dns_nameservers = ['10.8.8.8']
    router_name = 'test_router'

    network_body_value = {
        'network': {
            'name': 'test_network_private'
        }
    }

    def __init__(self, suffix='private'):
        self.suffix = suffix

    def _setUp(self):
        test_net = network.create_network(self.network_body_value)
        test_net_id = test_net['network']['id']

        body_subnet = {
            'subnets': [
                {'name': self.subnet_name,
                 'cidr': self.cidr,
                 'ip_version': self.ip_version,
                 'gateway_ip': self.gateway_ip,
                 'dns_nameservers': self.dns_nameservers,
                 'network_id': test_net_id}
            ]
        }
        network.create_subnet(body=body_subnet)




