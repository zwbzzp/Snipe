网络模式已知问题
==========================

nova-network 网络
----------------------

在部署时 nova-network 网络采用 multi-host 模式，那么目前只允许使用一个 nova-network 网络，所有的 vm 都应该接入到这个 nova-network 网络中。

由于 nova-network 网络要逐步被淘汰，目前的代码只为兼容性保留，后期逐步应迁移到 neutron 网络

neutron 网络
----------------------

使用 neturon 网络创建 vm 时，应该总传入一个 net-id ，然后 openstack 根据 net-id 在网络中选择一个子网（按照最小负载原则）。

每个子网都需要连接到一个虚拟路由器（无论是外部路由还是内部路由），才能访问到 nova 元数据服务，从中获取 vm 初始化信息。

目前的网络访问粒度是基于 net-id ，后期可提升到 subnet 和 port-id ，让网络定制可更加精细，并支持与外部网络的集成（如直接接入到外部的 vlan ）

与外部网络 vlan 集成时（即 openstack 内部网络直接与其它外部网络使用同一交换机，但通过 vlan 隔离，openstack 本身外部端口与内部网络必须 vlan 隔离），内部网络的 dhcp 只为内部 vm 服务，不影响外部 dhcp 。

neutron 节点可能成为单点，需要通过 vrrp 和 dvr 提供 HA 。
