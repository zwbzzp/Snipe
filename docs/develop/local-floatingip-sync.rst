本地 Floating ip 同步进程
==============================

概述
------------------------------

Floating ip sync 是一个在系统启动或管理员指定时间（系统维护时）调用的程序，用来把服务器端 openstack 的 floating ip 同步到本地数据库，解决批量绑定 floating ip 时的同步问题和性能问题


为什么需要 Floating ip sync
------------------------------
为虚拟机绑定 floating ip 的过程可以分为以下几个步骤：

1. 首先，向 openstack 查询可用 floating ip 的列表

2. 从返回的可用 floating ip 列表中选择一个

3. 向 openstack 发送请求，把选定的 floating ip 绑定到制定虚拟机。这时，floating ip 的状态才会被置为已占用

以上 floating ip 的绑定过程存在一些问题：

1. 同步问题，假如多个虚拟机同时需要绑定 floating ip，这时多个虚拟机会同时竞争同一个 floating ip，导致某些虚拟机绑定 floating ip 失败。例如，vm_1
   与 vm_2 同时进行步骤1，向 openstack 请求可用的 floating ip 列表，这时返回的他们获取到的 floating ip 列表是相同的。然后进行步骤2，从可以
   floating ip 列表中获取一个。假如这时候 vm_1 与 vm_2 获取到的是同一个 ip，例如 172.18.215.7，并进行步骤3，向 openstack 发送绑定请求。
   假设 vm_1 的请求首先被执行，ip 172.18.215.7 被绑定到 vm_1 上，然后 vm_2 的请求被执行，这时，ip 172.18.215.7 会被重新绑定到 vm_2 上，导致
   vm_1 没有绑定到任何 floating ip。

2. 性能问题，每次的 floating ip 绑定都需要向 openstack 查询可用 floating ip 列表，当大量虚拟机并发绑定 floating ip 时候会造成一定的性能损耗


解决方法
------------------------------
在管理系统本地维护一份 openstack 上的 floating ip 列表，在系统启动时或管理员调用时与 openstack 端 floating ip 列表的同步。原有向 openstack 获取 可用 floating ip 的步骤改为向
本地的 floating ip 列表获取可用 ip，并即时锁定和占用被选定的 ip，然后再作绑定。这样不仅解决了以上提及的当多个虚拟机并发绑定 floating ip 时候发生的同步问题，还减少了对 openstack 的
请求，提升了性能。系统结构如下图所示 ：：

    openstack floating ip list <=== sync ===> local floating ip list === get available ip ===> vm bind floating ip


数据模型
------------------------------

floating_ips ::

    ref_id                  floating ip 在 openstack 端的 id
    ip_address              ip 地址
    external_network_id     ip 地址所属的外部网络 id
    status                  ip 的状态，由两种，为 active 和 down，意思分别为已经被占用和未被占用


运行步骤
------------------------------

1. 运行 phoenix/src/phoenix/db/init_db.py 初始化 floating ip 本地数据库

2. 配置文件 phoenix/src/etc/phoenix.ini 项目 connection 配置如下，使用mysql数据库 ：：

    connection = 'mysql+pymysql://root:admin123@127.0.0.1:3306/phoenix'

3. 单独进程运行 phoenix/src/phoenix/cloud/openstack/sync_openstack.py

