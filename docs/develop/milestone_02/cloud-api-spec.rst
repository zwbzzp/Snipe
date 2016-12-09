cloud 模块 API 概述
==============================

compute API
------------------------------

    add_ip
    remove_ip

create_image
evacuate
    force_delete
lock
    pause
    reboot
    rebuild
rescue
    resume

    resize
    confirm_resize
    revert_pending_resize

shelve
shelf-offload
unshelve

start
    stop
    suspend
    delete

unlock
    unpause
unrescue

    add_security_group
    remove_security_group



image API
------------------------------

* 获取镜像
* 移除镜像

network API
------------------------------

如下接口的实现应支持 neutron 和 nova-network 两类网络

* 获取 floating ip
* 绑定 floating ip 到虚拟机
* floating ip 与虚拟机解除绑定

* TODO: vnp 部分

* nova-network
list
get
delete
create
disassociate
associate_host
associate_project
add

* neutron
ext	client extension hook
quotas
extension extensions on server side
port

network
subnet
subnet_pool
router
address_scope
interface_to_router add an internal interface to router
gateway_to_router add an external gateway to router

floating_ip
security_group
security_group_rule
vnpservice
ipec_site_connection
ikepolicy

    loadbalancer
    listener
    lbaas_pool
    lbaas_healthmonitor
    lbaas_member
    loadbalancer_vip
    loadbalancer_pool
    loadbalancer_member
    loadbalancer_healthmonitor

qos_queue
agent
gateway
gateway_device
dhcp_agent
l3_agent_and_router

firewall
firewall_rule
firewall_policy
firewall_policy_rule

    lbaas_agent_and_pool
    lbaas_agent_and_loadbalancer

service_provider
credential
network_profile
policy_profile

metering_label
metering_label_rule
network_partition
rbac_policy
qos_policy
qos_rule_type
bandwidth_limit_rule


storage API
------------------------------

* 新建共享存储
* 绑定共享存储到虚拟机
* 共享存储与虚拟机解除绑定
* 删除共享存储

* 新建个人存储
* 绑定个人存储到虚拟机
* 解除个人存储到虚拟机
* 删除个人存储
