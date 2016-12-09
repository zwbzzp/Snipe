如何配置和运行 MYSQL 数据库
===========================


运行 mysql
---------------------------

在开始前，阅读 `如何安装 docker 和 docker-compose 作为开发设施` ，并安装好 docker 环境。

下载需要的镜像 ::

    docker pull scm.vinzor.org:5000/mysql
    docker tag scm.vinzor.org:5000/mysql mysql

进入到 `infras` 目录中，运行 ::

    docker-compose -f mysql.yml -p phoenix up -d

docker-compose 会自动下载 mysql 的镜像，并运行起来。


建立 phoenix 数据库
--------------------------

使用 mysql-workbench 客户端，或者 mysql 命令行工具，连接到 mysql 容器，具体的端口和连接口令见 mysql.yml 配置文件。

mysql 的 ip 与 docker 虚拟机的 ip 一致，在 virtualbox 中通过命令可查看 ::

    docker env default

如果使用命令行工具，使用下面的用户创建数据库 ::

    mysql -uroot -padmin123 -h <docker vm ip> -e "create database phoenix default character set utf8"


设置 docker 虚拟机的 nat 映射
-------------------------------

在 virtualbox 中，设置 docker default 虚拟机的网络，在 `网络 -> 网卡1 （连接方式为 NAT ） -> 端口转发 ` 中，添加一个端口转发规则

+-------+--------+------------+-------+------------+
| 名称  |  协议  | 主机 ip    |  端口 |  子系统端口|
+=======+========+============+=======+============+
| mysql |  tcp   | 127.0.0.1  | 3306  |  3306      |
+-------+--------+------------+-------+------------+



初始化并升级数据库表
-----------------

激活 virtualenv 并在 `src/web` 目录下，运行 ::

    python manage.py db upgrade

如修改数据模型后更新数据库结构，运行 ::

    python manage.py db migrate -m '<更新信息>'

alembic 会自动在生成数据库升级指令文件，但如果同时增加和删除字段等，升级指令有时不正确，需要手工修改

指令文件的命名为 `yyyymmdd_版本号_信息`, 数据库指令文件必须通过评审，未经过评审的数据库指令文件不能被 merge 到主分支。

然后重新更新数据库结构 ::

    python manage.py db upgrade
