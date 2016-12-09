ZooKeeper部署
===================================


一.安装Java环境
-----------------------------------

::

    ubuntu 12.04: sudo apt-get install openjdk-7-jre
    ubuntu 14.04: sudo apt-get update
                  sudo apt-get install default-jre
                  sudo apt-ge install default-jdk


二.下载ZooKeeper安装包
-----------------------------------

ZooKeeper官方下载地址_

.. _ZooKeeper官方下载地址: http://zookeeper.apache.org/releases.html

使用 3.4.8版本_

.. _3.4.8版本: http://apache.fayea.com/zookeeper/zookeeper-3.4.8/zookeeper-3.4.8.tar.gz


三.单节点模式
-----------------------------------

ZooKeeper是不需要编译安装的, 解压缩和修改相关的配置文件即可运行, 具体步骤如下:

1.解压缩 ::
    
    tar -zxvf zookeeper-3.4.8.tar.gz

2.复制样本配置文件 ::

    cd ./zookeeper-3.4.8/zookeeper-3.4.8/conf/
    cp zoo_sample.cfg zoo.cfg

3.修改复制后的配置文件的如下内容, 如果没有, 可以添加项 ::

    syncLimit=5 # Leader与Follower之间的最大响应时间单位，响应超过syncLimit*tickTime，Leader认为Follwer死掉，从服务器列表中删除Follwer。
    initLimit=10 # 投票选举新leader的初始化时间。
    tickTime=2000 # Zookeeper服务器心跳时间，单位毫秒
    clientPort=2181 # 连接端口
    dataDir=/home/hadoop/zookeeper/data # 数据持久化路径
    dataLogDir=/home/hadoop/zookeeper/log # 日志保存路径

4.到ZooKeeper的bin目录下启动ZooKeeperServer即可运行 ::

    ./zkServer.sh 

5.单机测试 ::

    ./zkCli.sh -server localhost:2181


四.多节点集群模式
-----------------------------------

多节点集群模式的搭建和单节点的基本一样, 不同的是需要在配置文件下添加集群中各服务器的信息, 例如 ::

    server.1=a.a.a.a:2888:3888
    server.2=b.b.b.b:2888:3888
    server.3=c.c.c.c:2888:3888

每个服务器的信息为 server.A=B:C:D ::

    A 是一个数字,表示这个是第几号服务器, B是这个服务器的ip地址
    C 是集群成员进行信息交换的端口号, 表示的是这个服务器与集群中的Leader服务器交换信息的端口
    D 是在Leader挂掉时专门用来进行选举的端口号

添加上述配置后还要创建ServerID标识 ::

    在配置文件中定义的data目录下创建名字为myid的文件, 并在里面写入相应的id, 假设a服务器在配置文件中定义为
    server.1=a.a.a.a:2888:3888, 则在a服务器中的myid文件里写入 1 

最后, 在各个服务器中启动ZooKeeperServer即可







