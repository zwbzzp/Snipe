ZooAgent安装
===================================

**说明: ZooAgent需要在每个计算节点上安装,用于监控计算节点的网络状态**

一.下载ZooAgent安装包
-----------------------------------

ZooAgent安装包 `ZooAgent-1.0.0.tar.gz` 在当前文档所在目录下


二.安装
-----------------------------------

解压安装 ::

    tar ZooAgent-1.0.0.tar.gz;
    cd ZooAgent;
    bash -x install.sh;


三.配置
-----------------------------------

ZooAgent的配置文件zooagent.conf在其安装目录下 ::

    ext_hosts = <ZooKeeper服务器外部网络IP:2181>
    mgmt_hosts = <ZooKeeper服务器管理网络IP:2181>

修改完毕,重启服务即可 ::

    service zooagent restart



