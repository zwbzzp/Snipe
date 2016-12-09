如何搭建开发环境 —— ubuntu
============================


源代码下载
----------------------------

安装和 virtualenv::

    sudo apt-get install git python-pip
    sudo pip install virtualenv

下载源代码::

    git clone ssh://git@172.18.231.4:2222/vinzor/phoenix.git

进入项目目录，配置 email 和 name::

    cd phoenix
    git config --local user.email <工作邮箱>
    git config --local user.name <姓名全拼>

在项目目录中，建立 virtualenv 目录（独立 python 安装环境，不影响系统原有的 python ）并安装依赖::

    virtualenv -p python3 .venv
    source .venv/bin/activate       # 激活项目的 ptyhon 环境
    pip install -r requirements.txt
    pip install -r requirements-docs.txt
    pip install -r requirements-tests.txt


pycharm 安装
-------------------------

下载和安装 pycharm，从官网 `http://www.jetbrains.com/pycharm/download/#section=windows <http://www.jetbrains.com/pycharm/download/#section=windows>`_ 下载并安装

打开 pycharm ，在 pycharm 中打开项目目录。对 pycharm 进行设置。

settings - editor - code style - line separator = unix and osx

settings - editor - code style - right margins  = 80

settings - editor - file encodings  = 全部 utf-8

settings - version control - git    = 如使用其它 git 实现，写入路径

settings - project:phoenix - project interpreter = virtualenv 中的 python 路径

settings - project:phoenix - project structure 标记 src 目录为 sources

settings - languages and frameworks - python template language 设置为 jinjia2

文件模板设置 settings - editor - file and code templates - python script ，内容为 ::

    # -*- encoding: utf-8 -*-
    # Copyright 2016 Vinzor Co.,Ltd.
    #
    # comment
    #
    # $DATE $USER : Init

docker 安装
------------------------

见 how-to-install-docker-docker-compose.rst
