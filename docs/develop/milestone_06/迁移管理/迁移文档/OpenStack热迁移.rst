OpenStack热迁移
===================================

**说明: 本文档是在已经安装好openstack的情况下说明如何使用NFS作为共享存储开启openstack的热迁移功能**


一.NFS服务器的部署
-----------------------------------

NFS服务器可以安装在控制节点上也可以安装在独立的一台机器上，其部署的步骤如下:

1.安装NFS服务器 ::

    sudo apt-get update
    sudo apt-get install nfs-kernel-server

2.IDMAPD配置[当ubuntu版本小于11.10时才需要] ::

    配置路径:/etc/default/nfs-kernel-server, 将NEED_IDMAPD的值置为yes

    NEED_IDMAPD=yes # only needed for Ubuntu 11.10 and earlier

3.确保/etc/idmapd.conf中的相关值为如下:

    [Mapping]
    Nobody-User = nobody
    Nobody-Group = nogroup

4.将/var/lib/nova/instances共享 ::

    编辑/etc/exports文件, 添加如下一行:

    /var/lib/nova/instances *(rw,fsid=0,insecure,no_subtree_check,async,no_root_squash)

    说明: *号表示任意地址均可访问, 如果需要限制某些网络才可以访问, 可将*号修改为x.x.x.x/xx的格式网段

5.给共享目录设置执行位以便qemu可以使用存放在该目录的镜像 ::

    chmod o+x /var/lib/nova/instances

6.重启服务 ::

    service nfs-kernel-server restart

7.到这步, NFS服务器算是搭建好了, 可使用如下命令在nfs服务器上测试是否可用 ::

    mount -t nfs -o nolock 127.0.0.1:/var/lib/nova/instances /mnt
    cd /mnt
    touch test
    cd /var/lib/nova/instances
    ls


二.NFS客户端的部署
-----------------------------------

需在每一台计算节点上配置

1.安装NFS客户端 ::

    apt-get install nfs-common portmap

2.IDMAPD配置[当ubuntu版本小于11.10时才需要] ::

    配置路径:/etc/default/nfs-kernel-server, 将NEED_IDMAPD的值置为yes

    NEED_IDMAPD=yes # only needed for Ubuntu 11.10 and earlier

3.挂载共享文件夹 ::

    mount -t nfs NFS-SERVER:/var/lib/nova/instances  /var/lib/nova/instances

    说明: NFS-SERVER为NFS服务器的IP地址

4.启用开机自动挂载 ::

    编辑/etc/fstab文件, 添加如下一句:

    NFS-SERVER:/var/lib/nova/instances  /var/lib/nova/instances nfs auto 0 0

5.检查挂载是否成功，并确保权限为如下所示 ::

    ls -ld /var/lib/nova/instances
    权限 -> drwxr-xr-x

6.确保共享目录在系统中是否被挂载成功 ::

    mount -a -v
    df -k #检查输出中是否有/var/lib/nova/instances

至此, NFS客户端也成功配置


三.热迁移配置
-----------------------------------

热迁移配置需要在每一台计算节点上进行设置

1.修改/etc/libvirt/libvirtd.conf, 检查一下几项参数是否如下所示一致 ::
    
    listen_tls = 0
    listen_tcp = 1
    auth_tcp = "none"

2.修改/etc/init/libvirt-bin.conf, 添加-l参数 ::

    env libvirtd_opts="-d -l"

3.修改/etc/default/libvirt-bin, 添加-l参数 ::

    libvirtd_opts="-d -l"

4.重启libvirt服务 ::

    service libvirt-bin stop
    service libvirt-bin start

5.确保nova、libvirt-qemu的UID和GID在各计算节点保持一致,需手动调整各计算节点的nova、libvirt-qemu的UID和GID

    * 首先,选择其中一个计算节点的nova的UID和GID作为参考, 或者自行选择两个整数作为nova的约定UID和GID, 但要保证约定的UID和GID
      未被占用,其他节点也需要执行相同的查看命令,并记录好uid和gid,后面需要使用 ::

        id nova
        # 输出: uid=110(nova) gid=117(nova) groups=117(nova),113(libvirtd)

    * 这里我们选取110和117作为nova的约定UID和GID, 然后在其他计算节点执行如下命令 ::

        id nova # 记录输出,譬如 uid=111(nova) gid=119(nova) groups=119(nova),121(libvirtd)
        usermod -u 110 nova
        groupmod -g 117 nova

    * 对libvirt-qemu也需要执行上述的过程 ::

        约定libvirt-qemu的UID和GID,例如200和300
        id libvirt-qemu # 记录输出, uid=112(libvirt-qemu) gid=120(kvm) groups=120(kvm)
        usermod -u 200 libvirtd-qemu
        groupmod -g 300 kvm

    * 修改好后需要在各修改过的计算节点上执行如下命令 ::

        service nova-api stop
        service libvirt-bin stop
        find / -uid 111 -exec chown nova {} \; # 111 is the old nova uid before change
        find / -uid 112 -exec chown libvirt-qemu {} \; # 112 is the old libvirt-qemu uid before change
        find / -gid 119 -exec chgrp nova {} \; # 119 is the old nova gid before change
        find / -gid 120 -exec chgrp kvm {} \; # 120 is the old libvirt-qemu gid before change
        service nova-api restart
        service libvirt-bin restart

6.修改openstack的nova配置, 启用热迁移功能 ::

    编辑/etc/nova/nova.conf 添加如下内容:
    [libvirt]
    live_migration_bandwidth = 0
    live_migration_flag = VIR_MIGRATE_UNDEFINE_SOURCE,VIR_MIGRATE_PEER2PEER,VIR_MIGRATE_LIVE,VIR_MIGRATE_TUNNELLED
    live_migration_uri = qemu+tcp://%s/system

7.重启nova-compute ::

    service nova-compute restart


四.修改/etc/hosts文件
-----------------------------------

将各个节点(包括自己)的hostname及对应的管理IP写进各节点的/etc/hosts文件, 格式为 ::

    <节点的IP地址>  <节点的主机名>

并将ip为127.0.1.1的行注释掉, 修改后重启网络即可


OpenStack热迁移
===================================

**说明: 本文档是在已经安装好openstack的情况下说明如何使用NFS作为共享存储开启openstack的热迁移功能**


一.NFS服务器的部署
-----------------------------------

NFS服务器可以安装在控制节点上也可以安装在独立的一台机器上，其部署的步骤如下:

1.安装NFS服务器 ::

    sudo apt-get update
    sudo apt-get install nfs-kernel-server

2.IDMAPD配置[当ubuntu版本小于11.10时才需要] ::

    配置路径:/etc/default/nfs-kernel-server, 将NEED_IDMAPD的值置为yes

    NEED_IDMAPD=yes # only needed for Ubuntu 11.10 and earlier

3.确保/etc/idmapd.conf中的相关值为如下:

    [Mapping]
    Nobody-User = nobody
    Nobody-Group = nogroup

4.将/var/lib/nova/instances共享 ::

    编辑/etc/exports文件, 添加如下一行:

    /var/lib/nova/instances *(rw,fsid=0,insecure,no_subtree_check,async,no_root_squash)

    说明: *号表示任意地址均可访问, 如果需要限制某些网络才可以访问, 可将*号修改为x.x.x.x/xx的格式网段

5.给共享目录设置执行位以便qemu可以使用存放在该目录的镜像 ::

    chmod o+x /var/lib/nova/instances

6.重启服务 ::

    service nfs-kernel-server restart

7.到这步, NFS服务器算是搭建好了, 可使用如下命令在nfs服务器上测试是否可用 ::

    mount -t nfs -o nolock 127.0.0.1:/var/lib/nova/instances /mnt
    cd /mnt
    touch test
    cd /var/lib/nova/instances
    ls


二.NFS客户端的部署
-----------------------------------

需在每一台计算节点上配置

1.安装NFS客户端 ::

    apt-get install nfs-common portmap

2.IDMAPD配置[当ubuntu版本小于11.10时才需要] ::

    配置路径:/etc/default/nfs-kernel-server, 将NEED_IDMAPD的值置为yes

    NEED_IDMAPD=yes # only needed for Ubuntu 11.10 and earlier

3.挂载共享文件夹 ::

    mount -t nfs NFS-SERVER:/var/lib/nova/instances  /var/lib/nova/instances

    说明: NFS-SERVER为NFS服务器的IP地址

4.启用开机自动挂载 ::

    编辑/etc/fstab文件, 添加如下一句:

    NFS-SERVER:/var/lib/nova/instances  /var/lib/nova/instances nfs auto 0 0

5.检查挂载是否成功，并确保权限为如下所示 ::

    ls -ld /var/lib/nova/instances
    权限 -> drwxr-xr-x

6.确保共享目录在系统中是否被挂载成功 ::

    mount -a -v
    df -k #检查输出中是否有/var/lib/nova/instances

至此, NFS客户端也成功配置


三.热迁移配置
-----------------------------------

热迁移配置需要在每一台计算节点上进行设置

1.修改/etc/libvirt/libvirtd.conf, 检查一下几项参数是否如下所示一致 ::
    
    listen_tls = 0
    listen_tcp = 1
    auth_tcp = "none"

2.修改/etc/init/libvirt-bin.conf, 添加-l参数 ::

    env libvirtd_opts="-d -l"

3.修改/etc/default/libvirt-bin, 添加-l参数 ::

    libvirtd_opts="-d -l"

4.重启libvirt服务 ::

    service libvirt-bin stop
    service libvirt-bin start

5.确保nova、libvirt-qemu的UID和GID在各计算节点保持一致,需手动调整各计算节点的nova、libvirt-qemu的UID和GID

    * 首先,选择其中一个计算节点的nova的UID和GID作为参考, 或者自行选择两个整数作为nova的约定UID和GID, 但要保证约定的UID和GID
      未被占用,其他节点也需要执行相同的查看命令,并记录好uid和gid,后面需要使用 ::

        id nova
        # 输出: uid=110(nova) gid=117(nova) groups=117(nova),113(libvirtd)

    * 这里我们选取110和117作为nova的约定UID和GID, 然后在其他计算节点执行如下命令 ::

        id nova # 记录输出,譬如 uid=111(nova) gid=119(nova) groups=119(nova),121(libvirtd)
        usermod -u 110 nova
        groupmod -g 117 nova

    * 对libvirt-qemu也需要执行上述的过程 ::

        约定libvirt-qemu的UID和GID,例如200和300
        id libvirt-qemu # 记录输出, uid=112(libvirt-qemu) gid=120(kvm) groups=120(kvm)
        usermod -u 200 libvirtd-qemu
        groupmod -g 300 kvm

    * 修改好后需要在各修改过的计算节点上执行如下命令 ::

        service nova-api stop
        service libvirt-bin stop
        find / -uid 111 -exec chown nova {} \; # 111 is the old nova uid before change
        find / -uid 112 -exec chown libvirt-qemu {} \; # 112 is the old libvirt-qemu uid before change
        find / -gid 119 -exec chgrp nova {} \; # 119 is the old nova gid before change
        find / -gid 120 -exec chgrp kvm {} \; # 120 is the old libvirt-qemu gid before change
        service nova-api restart
        service libvirt-bin restart

6.修改openstack的nova配置, 启用热迁移功能 ::

    编辑/etc/nova/nova.conf 添加如下内容:
    [libvirt]
    live_migration_bandwidth = 0
    live_migration_flag = VIR_MIGRATE_UNDEFINE_SOURCE,VIR_MIGRATE_PEER2PEER,VIR_MIGRATE_LIVE,VIR_MIGRATE_TUNNELLED
    live_migration_uri = qemu+tcp://%s/system

7.重启nova-compute ::

    service nova-compute restart


四.修改/etc/hosts文件
-----------------------------------

将各个节点(包括自己)的hostname及对应的管理IP写进各节点的/etc/hosts文件, 格式为 ::

    <节点的IP地址>  <节点的主机名>

并将ip为127.0.1.1的行注释掉, 修改后重启网络即可


五.配置免密码登录
-----------------------------------

配置nova节点间的免密码登录, 以便用于nova host-evacuate 和host-servers-migrate等操作

1.设置nova用户的shell, 默认情况下nova用户是无shell的 ::

    usermod -s /bin/bash nova

2.设置nova用户的密码, 建议设置为和openstack的密码一样, 如admin123 ::

    passwd nova

3.切换到nova用户 ::

    su - nova

4.生成公私钥对 ::

    ssh-keygen

5.对xxx.xxx.xxx.xxx服务器设置免密码认证 ::

    ssh-copy-id xxx.xxx.xxx.xxx

6.对所有服务器完成上述免密码认证操作后执行如下命令即可 ::

    cat << EOF > ~/.ssh/config
    Host *
        StrictHostKeyChecking no
        UserKnownHostsFile=/dev/null
    EOF


六.迁移说明
-----------------------------------

经过上述五大步骤的配置后, 我们就可以使用nfs作为oepnstack的热迁移所需要的共享存储,并开启了openstack的虚拟机迁移功能.冷迁移和热迁移的oepnstack的配置是一样的, 区别只在于是否使用了共享存储. ::

    a)热迁移的命令为: nova live-migration <vm name> <host>
    b)冷迁移的命令为: nova live-migration --block-migrate <vm name> <host>







