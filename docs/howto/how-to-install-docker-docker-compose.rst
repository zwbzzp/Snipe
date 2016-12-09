如何安装 docker 和 docker-compose 作为开发设施
==============================================

phoenix 项目将使用 docker 作为标准的开发设施，将 mysql 、 cobbler 等应用以 docker 方式运行和交付，统一开发、测试、生产部署环境。

docker 可从国内的镜像站点下载 `http://get.daocloud.io/ <http://get.daocloud.io/>`_ 。


Windows 和 OS X 安装
-----------------------

下载安装 docker-toolbox ， docker-toolbox 中已带有 docker-engine 和 docker-compose 等工具。


Linux 安装
-----------------------

根据不同的发行版下载，一般地::

    curl -sSL https://get.daocloud.io/docker | sh
    curl -L https://get.daocloud.io/docker/compose/releases/download/1.5.2/docker-compose-`uname -s`-`uname -m` > /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose

运行
-----------------------

一般，只需要运行 docker-compose 启动应用组::

    docker-compose up -f <compose.yml> -d

在运行时，如果本地没有 docker 镜像，需要等待镜像下载，要花很长的时间，考虑搭建一个私有的 docker-registry 内部使用。

在 windows 和 Mac 上，由于使用虚拟机的方式启动 docker ，需要先在随 docker-toolbox 安装的 virtualbox 中启动 default 的 docker 虚拟机。

在 windows 上打开 powershell ，加载环境变量（ `--shell` 参数按照系统改变，具体查看 `docker-machine --help` ） ::

     docker-machine env default --shell=powershell

示例的输出为 ::

    $Env:DOCKER_TLS_VERIFY = "1"
    $Env:DOCKER_HOST = "tcp://192.168.99.100:2376"
    $Env:DOCKER_CERT_PATH = "C:\Users\fengyc\.docker\machine\machines\default"
    $Env:DOCKER_MACHINE_NAME = "default"
    # Run this command to configure your shell:
    # C:\Program Files\Docker Toolbox\docker-machine.exe env default --shell=powershell | Invoke-Expression

那么运行最后一行来配置 powershell 环境变量。注意，由于 docker-machine 路径中存在空格，要用引号包围，如果 docker-machine 已在系统的 path 路径变量中，可省去路径 ::

    "C:\Program Files\Docker Toolbox\docker-machine.exe" env default --shell=powershell | Invoke-Expression

或 ::

    docker-machine env default --shell=powershell | Invoke-Expression

然后，就可以连接到虚拟机中的 docker ，用 docker 运行各种命令 ::

    docker --version
    docker images
    docker ps -a

Mac 上采用与 windows 类似的过程。


scm.vinzor.org:5000 镜像库
----------------------------

目前已在 scm.vinzor.org:5000 搭建 docker-registry 仓库，镜像文件可在 scm.vizor.org:8084 上检索。

1. Linux 上的配置方法
    在 shell 中，运行命令 ::

        mkdir -p '/etc/docker/certs.d/scm.vinzor.org:5000'
        cat > '/etc/docker/certs.d/scm.vinzor.org:5000/ca.crt' << EOF
        -----BEGIN CERTIFICATE-----
        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
        7klAa5FgDw==
        -----END CERTIFICATE-----
        EOF

    然后尝试下载一个 busybox 的测试镜像 ::

        docker pull scm.vinzor.org:5000/busybox
        docker tag scm.vinzor.org:5000/busybox busybox

2. Windows 和 MAC （临时方案，重启后证书被清理）
    windows 和 mac 上都要先登录到 docker 虚拟机中，打开终端，运行 ::

        docker-machine ssh default

    然后与 linux 相同，配置一个 ca.crt 后，退出 docker 虚拟机。

    最后，尝试下载一个 busybox 的测试镜像 ::

        docker pull scm.vinzor.org:5000/busybox
        docker tag scm.vinzor.org:5000/busybox busybox
