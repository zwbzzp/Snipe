如何搭建开发环境 —— windows
============================


源代码下载
----------------------------

从 gitlab 上，通过 msys-git 或 tortoise git ，从项目地址上下载源代码

安装 virtualenv （ windows 版本的 python3.4 一般自带 pip ） ::

    pip install virtualenv

进入项目目录，并建立 virtualenv 环境，如果 windows 中默认的 python 不是 python3 ，那么需要指定 python3 所在的路径 ::

    virtualenv -p [<python 路径 >] .venv
    .venv/Scripts/activate       # 激活项目的 ptyhon 环境
    pip install -r requirements.txt
    pip install -r requirements-docs.txt
    pip install -r requirements-tests.txt


pycharm 安装
-------------------------

下载和安装 pycharm，从官网 `http://www.jetbrains.com/pycharm/download/#section=windows <http://www.jetbrains.com/pycharm/download/#section=windows>`_ 下载并安装

打开 pycharm ，在 pycharm 中打开项目目录。对 pycharm 进行设置。

settings - editor - code style - line separator = unix and osx （ windows 下默认设置为 windows 类型回车换行 ，注意修改）

settings - editor - code style - right margins  = 80

settings - editor - file encodings  = 全部 utf-8 （ windows 下默认设置为 gbk ，注意修改）

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