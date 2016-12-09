# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# comment
#
# 2016/7/7 ChengKang : Init

from flask.ext.wtf import Form
from wtforms.widgets import *
from wtforms import StringField, SelectField, BooleanField, TextAreaField, HiddenField, IntegerField, ValidationError
from wtforms.validators import data_required, length, regexp, number_range, ip_address, EqualTo, optional
from phoenix.cloud import network as OpenstackNetworkService
from ..models import Desktop
from . import utils, settings
import netaddr
import logging

LOG = logging.getLogger(__name__)
is_neutron_network = OpenstackNetworkService.is_neutron_network()

###############################################################
#        Following forms only used in Neutron network         #
###############################################################
def get_external_network_choices():
    external_network_list = [("", "")]
    for external_net in utils.list_external_networks():
        net_id = external_net["id"]
        net_name = external_net["name"] or ("(" + net_id + ")")
        external_network_list.append((net_id, net_name))

    return external_network_list


def get_subnets_choices():
    subnet_list = [("", "")]
    try:
        networks = utils.network_list_for_tenant()
    except Exception as ex:
        LOG.error("Fetch network list for tenant raise error: %s" % str(ex))
    else:
        for n in networks:
            net_name = n["name"] + ": " if n["name"] else ''
            subnet_list += [(subnet["id"], "%s%s (%s)" % (net_name, subnet["cidr"], subnet["name"] or subnet["id"]))
                            for subnet in n["subnets"]]

    return subnet_list


def get_ip_version_choices():
    ip_versions = [("4", "IPv4"), ("6", "IPv6")]

    return ip_versions


class NetworkUpdateForm(Form):
    name = StringField('Name', validators=[data_required(), length(1, 64)])
    ID = StringField('ID', validators=[data_required(), length(1, 64)])
    admin_state_up = BooleanField("AdminStateUp", validators=[optional()], default=True)


class SubnetBaseForm(Form):
    ip_version = SelectField("IPVersion", choices=[], validators=[optional()])
    gateway_ip = StringField('GatewayIP', validators=[optional(), length(1, 256)])
    disable_gateway = BooleanField("DisableGateway", validators=[optional()], default=False)
    enable_dhcp = BooleanField("EnableDhcp", validators=[optional()], default=True)
    allocation_pools = TextAreaField("AllocationPools", validators=[optional(), length(1, 1000)])
    dns_nameservers = TextAreaField("DnsNameservers", validators=[optional(), length(1, 1000)])
    host_routes = TextAreaField("HostRoutes", validators=[optional(), length(1, 1000)])

    def __init__(self, *args, **kwargs):
        super(SubnetBaseForm, self).__init__(*args, **kwargs)
        self.ip_version.choices = get_ip_version_choices()


class NetworkCreateForm(SubnetBaseForm):
    name = StringField('Name', validators=[data_required(), length(1, 64)])
    admin_state_up = BooleanField("AdminStateUp", validators=[optional()], default=True)
    create_subnet = BooleanField("CreateSubnet", validators=[optional()], default=True)
    subnet_name = StringField('SubnetName', validators=[optional(), length(1, 64)])
    subnet_cidr = StringField('SubnetCidr', validators=[optional(), length(1, 256)])


class SubnetCreateForm(SubnetBaseForm):
    network_id = StringField('NetworkId', validators=[data_required(), length(1, 64)])
    name = StringField('Name', validators=[data_required(), length(1, 64)])
    cidr = StringField('Cidr', validators=[data_required(), length(1, 256)])


class SubnetUpdateForm(SubnetBaseForm):
    subnet_id = StringField('SubnetId', validators=[data_required(), length(1, 64)])
    name = StringField('Name', validators=[data_required(), length(1, 64)])
    cidr = StringField('Cidr', validators=[data_required(), length(1, 256)])


class PortCreateForm(Form):
    network_id = StringField("NetworkId", validators=[data_required(), length(1, 64)])
    name = StringField("Name", validators=[data_required(), length(1, 64)])
    admin_state_up = BooleanField("AdminStateUp", validators=[optional()], default=True)
    device_id = StringField("DeviceId", validators=[optional(), length(1, 256)])
    device_owner = StringField("DeviceOwner", validators=[optional(), length(1, 64)])


class PortUpdateForm(Form):
    port_id = StringField("ID", validators=[data_required(), length(1, 64)])
    name = StringField("Name", validators=[data_required(), length(1, 64)])
    admin_state_up = BooleanField("AdminStateUp", validators=[optional()])
    device_id = StringField("DeviceId", validators=[optional(), length(1, 256)])
    device_owner = StringField("DeviceOwner", validators=[optional(), length(1, 64)])


class RouterCreateForm(Form):
    name = StringField("Name", validators=[data_required(), length(1, 64)])


class RouterAddGatewayForm(Form):
    router_id = StringField("ID", validators=[data_required(), length(1, 64)])
    external_network_id = SelectField("ExternalNetworkId", choices=[], validators=[data_required()])

    def __init__(self, *args, **kwargs):
        super(RouterAddGatewayForm, self).__init__(*args, **kwargs)
        self.external_network_id.choices = get_external_network_choices()


class RouterAddInterfaceForm(Form):
    router_id = StringField("RouterID", validators=[data_required(), length(1, 64)])
    subnet_id = SelectField("SubnetID", choices=[], validators=[data_required(), length(1, 64)])
    ip_address = StringField("IpAddress", validators=[optional(), length(1, 256), ip_address()])

    def __init__(self, *args, **kwargs):
        super(RouterAddInterfaceForm, self).__init__(*args, **kwargs)
        self.subnet_id.choices = get_subnets_choices()


###############################################################
#Following forms used in both Neutron and Nova-network network#
###############################################################
def get_desktop_choices():
    choices = [("", "")]
    desktops = Desktop.query.all()
    choices.extend([(str(desktop.id), desktop.name) for desktop in desktops])

    return choices


def get_floating_ip_pools_choices():
    choices = [("", "")]
    if is_neutron_network:
        for external_net in utils.list_external_networks():
            net_id = external_net["id"]
            net_name = external_net["name"] or ("(" + net_id + ")")
            choices.append((net_id, net_name))
    else:
        for pool in OpenstackNetworkService.list_floating_ip_pools():
            choices.append((pool.name, pool.name))

    return choices


class AssociateIPForm(Form):
    """
    The form used to associate a floating ip with one desktop
    """
    fip_ref_id = StringField('FloatingipRefID', validators=[data_required(), length(1, 64)])
    desktop_id = SelectField('DesktopID', choices=[], validators=[data_required()])

    def __init__(self, *args, **kwargs):
        super(AssociateIPForm, self).__init__(*args, **kwargs)
        self.desktop_id.choices = get_desktop_choices()


class AllocateIPForm(Form):
    """
    The form used to allocate floating ip for current tenant
    """
    fip_pool = SelectField('FloatingIpPool', choices=[], validators=[data_required()])

    def __init__(self, *args, **kwargs):
        super(AllocateIPForm, self).__init__(*args, **kwargs)
        self.fip_pool.choices = get_floating_ip_pools_choices()


class SecurityGroupCreateForm(Form):
    """
    The form used to create a security group
    """
    name = StringField('SecurityGroupName', validators=[data_required(), length(1, 64)])
    description = TextAreaField("SecurityGroupDescription", validators=[data_required(), length(1, 200)])


class SecurityGroupUpdateForm(Form):
    """
    The form used to update a security group
    """
    ID = StringField('SecurityGroupId', validators=[data_required(), length(1, 64)])
    name = StringField('SecurityGroupName', validators=[data_required(), length(1, 64)])
    description = TextAreaField("SecurityGroupDescription", validators=[data_required(), length(1, 200)])


class SecgroupRuleCreateForm(Form):
    """
    The form used to create a security group rule
    """
    ID = HiddenField('SecurityGroupId', validators=[data_required(), length(1, 64)])
    rule_menu = SelectField('规则', choices=[], 
                            validators=[data_required()], 
                            render_kw={'class': 'switchable select2', 'data-slug': 'rule_menu'})
    direction = SelectField('方向',
                            validators=[optional()],
                            choices=[],
                            render_kw={'class': 'switched select2', 'data-switch-on': 'rule_menu', 
                                       'data-rule_menu-tcp': 'Direction',
                                       'data-rule_menu-udp': 'Direction',
                                       'data-rule_menu-icmp': 'Direction',
                                       'data-rule_menu-custom': 'Direction',
                                       'data-rule_menu-all_tcp': 'Direction',
                                       'data-rule_menu-all_udp': 'Direction',
                                       'data-rule_menu-all_icmp': 'Direction'})
    ip_protocol = IntegerField('IP协议', validators=[optional()], 
                               description='输入一个0到255之间的整数值(或输入-1作为通配符)',
                               render_kw={'class': 'switched', 'data-switch-on': 'rule_menu', 
                                          'data-rule_menu-custom': 'Ip Protocol'})
    port_or_range = SelectField('打开端口', 
                                choices=[('port', '端口'), ('range', '端口范围')], 
                                validators=[optional()], 
                                render_kw={'class': 'switchable switched select2',
                                           'data-slug': 'range',
                                           'data-switch-on': 'rule_menu',
                                           'data-rule_menu-tcp': 'Open Port',
                                           'data-rule_menu-udp': 'Open Port'})
    port = IntegerField('端口', validators=[optional()], 
                        description='输入大于1小于65535的整数', 
                        render_kw={'class': 'switched',
                                   'data-switch-on': 'range',
                                   'data-range-port': 'Port'})
    from_port = IntegerField('起始端口号', validators=[optional()], 
                             description='输入大于1小于65535的整数', 
                             render_kw={'class': 'switched',
                                        'data-switch-on': 'range',
                                        'data-range-range': 'From Port'})
    to_port = IntegerField('终止端口号', validators=[optional()], 
                           description='输入大于1小于65535的整数',
                           render_kw={'class': 'switched',
                                      'data-switch-on': 'range',
                                      'data-range-range': 'To Port'})
    icmp_type = IntegerField('类型', validators=[optional()], 
                             description='请输入ICMP类型值范围(-1:255)',
                             render_kw={'class': 'switched',
                                        'data-switch-on': 'rule_menu',
                                        'data-rule_menu-icmp': 'Type'})
    icmp_code = IntegerField('编码', validators=[optional()], 
                             description='请输入ICMP代码范围(-1:255)',
                             render_kw={'class': 'switched',
                                        'data-switch-on': 'rule_menu',
                                        'data-rule_menu-icmp': 'Code'})
    remote = SelectField('远程',
                         validators=[optional()],
                         choices=[('cidr', 'CIDR'), ('sg', '安全组')],
                         description='指定合法的ip范围,选择"CIDR";如果允许另外的安全组的成员访问,选择"安全组"',
                         render_kw={'class': 'switchable select2', 
                                    'data-slug': 'remote'})
    cidr = StringField('CIDR', validators=[optional(), length(1, 256)], 
                       description='无类别域间路由(e.g. 192.168.0.0/24)',
                       default='0.0.0.0/0',
                       render_kw={'class': 'switched', 
                                  'data-switch-on': 'remote',
                                  'data-remote-cidr': 'CIDR'})
    security_group = SelectField('安全组',
                                 validators=[optional()],
                                 render_kw={'class': 'switched select2',
                                            'data-switch-on': 'remote',
                                            'data-remote-sg': 'Security Group'})
    # When cidr is used ethertype is determined from IP version of cidr.
    # When source group, ethertype needs to be specified explicitly.
    ethertype = SelectField('输入类型', 
                            choices=[('IPv4', 'IPv4'), ('IPv6', 'IPv6')], 
                            validators=[optional()],
                            render_kw={'class': 'switched select2',
                                       'data-slug': 'ethertype',
                                       'data-switch-on': 'remote',
                                       'data-remote-sg': 'Ether Type'})

    def __init__(self, *args, **kwargs):
        secgroup_id = kwargs.pop('secgroup_id', None)
        super(SecgroupRuleCreateForm, self).__init__(*args, **kwargs)
        # Determine if there are security groups available for the
        # remote group option; add the choices and enable the option if so.
        sg_list = OpenstackNetworkService.list_security_groups(tenant_id=utils.get_tenant_id())
        self.security_group.choices = [(str(sg['id']), ('%s (当前)' % sg['name']) \
                                       if (secgroup_id and str(sg['id']) == secgroup_id) else sg['name']) \
                                       for sg in sg_list]

        # choices for rule menu
        backend = 'neutron' if is_neutron_network else 'nova'
        rules_dict = settings.SECURITY_GROUP_RULES
        common_rules = [(k, rules_dict[k]['name']) for k in rules_dict if rules_dict[k].get('backend', backend) == backend]
        common_rules.sort()
        custom_rules = [('tcp', '定制TCP规则'),
                        ('udp', '定制UDP规则'),
                        ('icmp', '定制ICMP规则')]
        if backend == 'neutron':
            custom_rules.append(('custom', '其他协议'))
        self.rule_menu.choices = custom_rules + common_rules
        self.rules = rules_dict

        if backend == 'neutron':
            self.direction.choices = [('ingress', '入口'), ('egress', '出口')]
        else:
            # direction and ethertype are not supported in Nova secgroup.
            del self.direction
            del self.ethertype
            # ip_protocol field is to specify arbitrary protocol number
            # and it is available only for neutron security group.
            del self.ip_protocol
    
    @property
    def data(self):
        cleaned_data = super(SecgroupRuleCreateForm, self).data

        def update_cleaned_data(key, value):
            cleaned_data[key] = value
            self.errors.pop(key, None)

        rule_menu = cleaned_data.get('rule_menu')
        port_or_range = cleaned_data.get('port_or_range')
        remote = cleaned_data.get('remote')

        icmp_type = cleaned_data.get('icmp_type', None)
        icmp_code = cleaned_data.get('icmp_code', None)

        from_port = cleaned_data.get('from_port', None)
        to_port = cleaned_data.get('to_port', None)
        port = cleaned_data.get('port', None)

        if rule_menu == 'icmp':
            update_cleaned_data('ip_protocol', rule_menu)

            if icmp_type is None:
                msg = 'The ICMP type is invalid.'
                raise ValidationError(msg)
            if icmp_code is None:
                msg = 'The ICMP code is invalid.'
                raise ValidationError(msg)
            if icmp_type not in range(-1, 256):
                msg = 'The ICMP type not in range (-1, 255)'
                raise ValidationError(msg)
            if icmp_code not in range(-1, 256):
                msg = 'The ICMP code not in range (-1, 255)'
                raise ValidationError(msg)

            update_cleaned_data('from_port', icmp_type)
            update_cleaned_data('to_port', icmp_code)
            update_cleaned_data('port', None)
        elif rule_menu == 'tcp' or rule_menu == 'udp':
            update_cleaned_data('ip_protocol', rule_menu)
            update_cleaned_data('icmp_code', None)
            update_cleaned_data('icmp_type', None)
            if port_or_range == 'port':
                if not port:
                    msg = 'The specified port is invalid.'
                    raise ValidationError(msg)
                elif port not in range(1, 65536):
                    msg = 'The port not in range (1, 65535)'
                    raise ValidationError(msg)

                update_cleaned_data('from_port', port)
                update_cleaned_data('to_port', port)
            else:
                if not from_port:
                    msg = 'The "from" port number is invalid.'
                    raise ValidationError(msg)
                elif from_port not in range(1, 65536):
                    msg = 'The "from" port number not in range(1, 65535)'
                    raise ValidationError(msg)
                if not to_port:
                    msg = 'The "to" port number is invalid.'
                    raise ValidationError(msg)
                elif to_port not in range(1, 65536):
                    msg = 'The "to" port number not in range(1, 65535)'
                    raise ValidationError(msg)

                if to_port < from_port:
                    msg = 'The "to" port number must be greater than ' \
                           'or equal to the "from" port number.'
                    raise ValidationError(msg)
        elif rule_menu == 'custom':
            pass
        else:
            cleaned_data['ip_protocol'] = self.rules[rule_menu]['ip_protocol']
            cleaned_data['from_port'] = int(self.rules[rule_menu]['from_port'])
            cleaned_data['to_port'] = int(self.rules[rule_menu]['to_port'])
            if rule_menu not in ['all_tcp', 'all_udp', 'all_icmp']:
                cleaned_data['direction'] = self.rules[rule_menu].get('direction')

        if not cleaned_data.get('direction'):
            cleaned_data['direction'] = 'ingress'
        if not cleaned_data.get('ethertype'):
            cleaned_data['ethertype'] = 'IPv4'

        if remote == 'cidr':
            update_cleaned_data('security_group', None)

            cidr = cleaned_data.get('cidr', None)
            if not cidr:
                msg = 'CIDR must be specified.'
                raise ValidationError(msg)
            else:
                ip_ver = netaddr.IPNetwork(cidr).version
                cleaned_data['ethertype'] = 'IPv6' if ip_ver == 6 else 'IPv4'
        else:
            update_cleaned_data('cidr', None)

        return cleaned_data






                





        
        









