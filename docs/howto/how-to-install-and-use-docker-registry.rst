Docker Registry Deployment
========================================

以下操作均在服务器主机中进行

0. 安装Docker Engine并启动Docker Deamon
----------------------------------------

Reference: Install Docker: https://docs.docker.com/linux/step_one/

1）运行官方脚本安装::

    $ wget -qO- https://get.docker.com/ | sh


2）将当前用户(ubuntu)添加到docker群组中::

    $ sudo usermod -aG docker ubuntu

3）启动服务::

    $ sudo service docker start
    Redirecting to /bin/systemctl start  docker.service

4）查看版本::

    $ docker version
    Client:
     Version:      1.9.1
     API version:  1.21
     Go version:   go1.4.2
     Git commit:   a34a1d5
     Built:        Fri Nov 20 13:25:01 UTC 2015
     OS/Arch:      linux/amd64
    Server:
     Version:      1.9.1
     API version:  1.21
     Go version:   go1.4.2
     Git commit:   a34a1d5
     Built:        Fri Nov 20 13:25:01 UTC 2015
     OS/Arch:      linux/amd64

5）测试Docker：从Docker Hub中下载并运行镜像hello-world::

    $ docker run hello-world

1. 下载docker-registry镜像
----------------------------------------

::

    $ docker pull registry:2

2. 创建镜像、证书、认证（可选）存放目录
----------------------------------------

::

    $ sudo mkdir -p /opt/docker/registry/data
    $ sudo mkdir -p /opt/docker/registry/certs
    $ sudo mkdir -p /opt/docker/registry/auth

3. 配置主机名（因为有域名，省略此步骤）
----------------------------------------

假设Docker Registry是部署到172.18.231.4的，添加主机名和IP到/etc/hosts::

    $ sudo sed -i '$a 172.18.231.4  scm.vinzor.org' /etc/hosts

4. 证书和认证
----------------------------------------

Docker要求在使用registry，除了访问localhost外，都要用TLS保护。

1）生成证书::

    $ sudo openssl req -newkey rsa:4096 -nodes -sha256 -keyout /opt/docker/registry/certs/docker-registry.key -x509 -days 365 -out /opt/docker/registry/certs/docker-registry.crt
    writing new private key to '/opt/docker/registry/certs/docker-registry.key'
    -----
    You are about to be asked to enter information that will be incorporated into your certificate request.
    What you are about to enter is what is called a Distinguished Name or a DN.
    There are quite a few fields but you can leave some blank
    For some fields there will be a default value, If you enter '.', the field will be left blank.
    -----
    Country Name (2 letter code) [XX]:CN
    State or Province Name (full name) []:GuangDong
    Locality Name (eg, city) [Default City]:Guangzhou
    Organization Name (eg, company) [Default Company Ltd]:vinzor
    Organizational Unit Name (eg, section) []:
    Common Name (eg, your name or your server' s hostname) []:scm.vinzor.org
    Email Address []:

注意，Common Name是Docker Registry的主机名，是镜像上传下载的关键路径

2）生成认证（可选）::

    $ docker run --entrypoint htpasswd registry:2 -Bbn [username] [password] > /tmp/docker-registry.htpasswd
    $ sudo mv /tmp/docker-registry.htpasswd /opt/docker/registry/auth/docker-registry.htpasswd

5. 启动Docker Registry
----------------------------------------

A 方式一：shell::

    $ docker run -d -p 5000:5000 --restart=always --name registry \
             -v /opt/docker/registry/data:/var/lib/registry \
             -v /opt/docker/registry/auth:/auth \
             -e "REGISTRY_AUTH=htpasswd" \
             -e "REGISTRY_AUTH_HTPASSWD_REALM=Registry Realm" \
             -e REGISTRY_AUTH_HTPASSWD_PATH=/auth/docker-registry.htpasswd \
             -v /opt/docker/registry/certs:/certs \
             -e REGISTRY_HTTP_TLS_CERTIFICATE=/certs/docker-registry.crt \
             -e REGISTRY_HTTP_TLS_KEY=/certs/docker-registry.key \
             registry:2
B 方式二：docker-compose
Docker Compose提供一个简单的基于YAML配置语言,用于描述和组装多容器的应用。 
使用Docker Compose可以定义和运行复杂的应用,因为在YAML配置文件中的定义看起来，虽然相比于shell只是形式上的不同。但更直观，推荐使用这种方式
如果安装过docker-compose，则跳到第三步
1）安装docker-compose::

    $ curl -L https://github.com/docker/compose/releases/download/1.5.2/docker-compose-`uname -s`-`uname -m` > sudo /tmp/docker-compose
    $ sudo mv /tmp/docker-compose /usr/local/bin/
    $ sudo chmod +x /usr/local/bin/docker-compose

2）测试安装::

    $ docker-compose --version
    docker-compose version: 1.5.2

3）后台执行docker-compose，启动Docker Registry::

    $ docker-compose up -d
    Creating ubuntu_registry_1

docker-compose.yml::

    registry:
      restart: always
      image: registry:2
      ports:
        - 5000:5000
      environment:
        - REGISTRY_HTTP_TLS_CERTIFICATE=/certs/docker-registry.crt
        - REGISTRY_HTTP_TLS_KEY=/certs/docker-registry.key
        - REGISTRY_AUTH=htpasswd
        - REGISTRY_AUTH_HTPASSWD_PATH=/auth/docker-registry.htpasswd
        - REGISTRY_AUTH_HTPASSWD_REALM=Registry Realm
      volumes:
        - /opt/docker/registry/data:/var/lib/registry
        - /opt/docker/registry/certs:/certs
        - /opt/docker/registry/auth:/auth

6.为服务器添加ca.crt
------------------------------------

::

    $ sudo mkdir -p /etc/docker/certs.d/scm.vinzor.org:5000
    $ sudo cp /opt/docker/registry/certs/docker-registry.crt /etc/docker/certs.d/scm.vinzor.org:5000/ca.crt

7.测试搭建
------------------------------------

1）测试无认证上传
因为从Docker Hub拉下来的hello-world默认上传地址是docker.io，需要修改镜像tag，下一步才能将镜像push到Docker Registry::

    $ docker tag hello-world scm.vinzor.org:5000/hello-world
    $ docker push scm.vinzor.org:5000/hello-world
    The push refers to a repository [scm.vinzor.org:5000/hello-world] (len: 1)
    0a6ba66e537a: Image push failed 
    Head https://scm.vinzor.org:5000/v2/hello-world/blobs/sha256:a3ed95caeb02ffe68cdd9fd84406680ae93d633cb16422d00e8a7c22955b46d4: no basic auth credentials

如果上传失败，根据提示信息知道是没有认证，表示实现了认证机制，进行下一步测试

2）测试认证上传
-登录Docker Registry（未设置认证则跳过此步骤）::

    $ docker login scm.vinzor.org:5000
    Username: [username]
    Password: [password]
    Email:
    Login Succeeded

如果遇到如下问题，原因是未添加证书 根据提示有两种解决方法::

    Username (vinzor): 
    Error response from daemon: invalid registry endpoint https://scm.vinzor.org:5000/v0/: unable to ping registry endpoint https://scm.vinzor.org:5000/v0/
    v2 ping attempt failed with error: Get https://scm.vinzor.org:5000/v2/: x509: certificate signed by unknown authority (possibly because of "crypto/rsa: verification error" while trying to verify candidate authority certificate "scm.vinzor.org")
     v1 ping attempt failed with error: Get https://scm.vinzor.org:5000/v1/_ping: x509: certificate signed by unknown authority (possibly because of "crypto/rsa: verification error" while trying to verify candidate authority certificate "scm.vinzor.org"). If this private registry supports only HTTP or HTTPS with an unknown CA certificate, please add `--insecure-registry scm.vinzor.org:5000` to the daemon's arguments. In the case of HTTPS, if you have access to the registry's CA certificate, no need for the flag; simply place the CA certificate at /etc/docker/certs.d/scm.vinzor.org:5000/ca.crt

方法一：则根据最后一句提示添加证书即可

方法二：如果是Ubuntu14.04，也可以在/etc/default/docker中添加下面一行::

    DOCKER_OPTS="$DOCKER_OPTS --insecure-registry= scm.vinzor.org:5000"

continue:然后重启Docker::

    $ sudo service docker restart

-上传本地镜像::

    $ docker push scm.vinzor.org:5000/hello-world
    The push refers to a repository [scm.vinzor.org:5000/hello-world] (len: 1)
    0a6ba66e537a: Pushed 
    b901d36b6f2f: Pushed 
    latest: digest: sha256:1c7adb1ac65df0bebb40cd4a84533f787148b102684b74cb27a1982967008e4b size: 2744

登录后，上传成功，进行下一步测试

3）测试认证下载
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

-删除本地镜像::

    $ docker rmi scm.vinzor.org:5000/hello-world
    Untagged: scm.vinzor.org:5000/hello-world:latest

-从Docker Registry中下载::

    $ docker pull scm.vinzor.org:5000/hello-world
    Using default tag: latest
    latest: Pulling from hello-world
    Digest: sha256:1c7adb1ac65df0bebb40cd4a84533f787148b102684b74cb27a1982967008e4b
    Status: Downloaded newer image for scm.vinzor.org:5000/hello-world:latest

测试完成

Docker Registry Usage
=================================

以下操作均在客户机中进行

0. 安装Docker Engine并启动Docker Deamon
----------------------------------------

Reference: Install Docker: https://docs.docker.com/linux/step_one/

1）运行官方脚本安装::

    $ wget -qO- https://get.docker.com/ | sh

2）将当前用户(ubuntu)添加到docker群组中::

    $ sudo usermod -aG docker ubuntu

3）启动服务::

    $ sudo service docker start
    Redirecting to /bin/systemctl start  docker.service

4）查看版本::

    $ docker version
    Client:
     Version:      1.9.1
     API version:  1.21
     Go version:   go1.4.2
     Git commit:   a34a1d5
     Built:        Fri Nov 20 13:25:01 UTC 2015
     OS/Arch:      linux/amd64
    Server:
     Version:      1.9.1
     API version:  1.21
     Go version:   go1.4.2
     Git commit:   a34a1d5
     Built:        Fri Nov 20 13:25:01 UTC 2015
     OS/Arch:      linux/amd64

5）测试Docker：从Docker Hub中下载并运行镜像hello-world::
 
   $ docker run hello-world

1. 配置主机名（因为有域名，省略此步骤）
----------------------------------------

假设Docker Registry是部署到172.18.231.4的，添加主机名和IP到/etc/hosts::

    $ sudo sed -i '$a 172.18.231.4  scm.vinzor.org' /etc/hosts

2.为客户机添加ca.crt
----------------------------------------

::

    $ sudo mkdir -p /etc/docker/certs.d/scm.vinzor.org:5000
    $ sudo cp ca.crt /etc/docker/certs.d/scm.vinzor.org:5000/

ca.crt证书在gitlab项目文件中

3.镜像使用
----------------------------------------

Reference: Get Start with Docker for linux: https://docs.docker.com/linux/

1）查看镜像

-查看Docker Registry镜像
无认证::

    $ curl -X GET https://scm.vinzor.org:5000/v2/_catalog -k

有认证::
    
    $ curl -X GET https://[username]:[password]@scm.vinzor.org:5000/v2/_catalog -k

-查看本地镜像::

    $ docker images

2）登录 （我们没设置认证，跳过此步骤）::

    $ docker login scm.vinzor.org:5000
    Username: [username]
    Password: [password]
    Email:
    Login Succeeded

如果出现了部署部分中测试认证中出现的错误，参考该部分的解决方法

3）下载::

    $ docker pull scm.vinzor.org:5000/hello-world

4）修改下载的镜像tag::

    $ docker tag scm.vinzor.org:5000/hello-world hello-world

5）上传

-镜像是从其它地方下载，需要先将tag改为scm.vinzor.org:5000/xxx的形式::

    $ docker tag ubuntu:14.04 scm.vinzor.org:5000/ubuntu:14.04

上面命令中的镜像名还可以是镜像的id，image id通过docker images查看. 样式如::

    $ docker tag 6ba66e537a scm.vinzor.org:5000/ubuntu:14.04

-上传镜像::

    $ docker push scm.vinzor.org:5000/ubuntu:14.04

6）删除本地镜像::

    $ docker rmi scm.vinzor.org:5000/hello-world
