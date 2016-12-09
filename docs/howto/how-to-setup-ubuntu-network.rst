如何在ubuntu内设置网络
==============================

* 查看网卡名称 ::

    sudo lshw -C network

* 如网卡名称不是ethx，可以更改网卡名称 ::

    sudo touch /etc/udev/rules.d/70-persistent-net.rules

    sudo vim /etc/udev/rules.d/70-persistent-net.rules

    添加如下行，更改网卡名称

    SUBSYSTEM=="net", ACTION=="add", ATTR{address}=="00:0c:29:90:08:77", NAME="eth0"

    SUBSYSTEM=="net", ACTION=="add", ATTR{address}=="00:0c:29:90:08:81", NAME="eth1"

    然后重启ubuntu

* 配置网卡为固定ip ::


    auto eth0
    iface eth0 inet static
    address 10.0.0.128
    netmask 255.255.255.0
    gateway 10.0.0.2
    dns-nameservers 10.8.8.8 114.114.114.114 8.8.8.8

* 重启网卡 ::

    sudo ifdown eth0
    sudo ifup eth0

* 如果 ping 不通 www.baidu.com，但可以 ping 通地址 202.108.22.5 则说明 dns 有问题。修改文件 resolv.conf 如下， 不用重启任何东西 ::

    nameserver 114.114.114.114
    nameserver 8.8.8.8
