启动测试服务器
=====================

web 应用在 `src/web` 目录下，以下的命令假定均在 `src/web` 目录下运行

安装依赖
---------------------

所有依赖应该在 virtualenv 下安装。

在 windows 中，可能会出现 pyYAML 编译错误的问题，需要安装一个 visual studio (VC) ，并在 virtualenv 加载编译环境变量（否则也可能会出现编译问题） ::

    <visual studio 安装目录>\VC\vcvarsall.bat x86 & set

然后，安装项目依赖。 virtualenv 下， ::

    pip install -r requirements.txt
    
配置信息
----------------------------------

配置文件为

    .env -> 记录从环境变量中加载的信息
    config.py -> 配置文件

更新数据库结构
----------------------------------

目前数据库使用一个 sqlite 文件，可随时删除或更新。

每次更新了数据模型时，都需要更新数据库结构，首先清理 migration 生成的数据库迁移脚本，清理 `migrations/versions` 目录下的 `*.py` 文件，并删除 sqlite 数据库文件 `*.sqlite`。

virtualenv 下，运行 ::

    python manage.py db migrate -m "init"
    python manage.py db upgrade
    python manage.py deploy
    
*不要迁入 migrate 后生成的数据库迁移脚本（migrations 目录），在数据库稳定后统一编译发布数据库脚本*

启动 rabbitmq (作为 celery 的 broker)
---------------------------------------------

在项目的 `infras/` 目录下，有 rabbitmq 的 docker-compose 启动配置文件，::

    docker-compose -f rabbitmq-management.yml -p phoenix up -d

并根据 howto 中的 `hot-to-setup-mysql.rst` 文档，类似地设置 rabbitmq 的端口映射

+-------+--------+------------+-------+------------+
| 名称  |  协议  | 主机 ip    |  端口 |  子系统端口|
+=======+========+============+=======+============+
| rb    |  tcp   | 127.0.0.1  | 5672  |  5672      |
+-------+--------+------------+-------+------------+
| rbweb |  tcp   | 127.0.0.1  | 15672 |  15672     |
+-------+--------+------------+-------+------------+

可通过 `127.0.0.1:15672` 查看 rabbitmq 队列，默认用户名和密码为 root admin123。

启动过一次后，以后在 docker 服务或虚拟机启动时会自动启动这个 rabbitmq 容器。

启动 celery beat 进程（调度）
----------------------------------

virtualenv 下，运行 ::

    python manage.py beat

或 ::

    celery beat -A manage.celery -S manage.DatabaseScheduler --loglevel=info

启动 celery worker 进程（worker）
-----------------------------------

virtualenv 下，运行 ::

    python manage.py worker

或 ::

    celery worker -A manage.celery --loglevel=info

启动 web 测试服务器
---------------------------------

virtualenv 下，运行 ::

    python manage.py runserver

通过 pycharm 注册命令
--------------------------------

pycharm 中，通过 `Run -> Edit Configrations...` 可注册一些常用的命令

注意
--------------------------------

生产环境下，应使用 supervisord 启动 celery worker/beat 和 uwsgi ，并开启 ssl
