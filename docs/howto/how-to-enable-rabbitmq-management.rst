打开 rabbitmq web 控制台
==============================

安装 rabbitmq 后，运行 ::

    rabbitmq-plugins enable rabbitmq_management

web 控制台的默认端口为 15672

如果使用 rabbitmq 带 management 的 docker 镜像，那么在默认情况下，已经打开了 web 控制台，
只要把本机到 docker 虚拟机的端口映射处理好，就可查看队列状态