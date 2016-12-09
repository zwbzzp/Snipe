如何安装配置和使用sphinx工具
========================

简介
------------------------

Sphinx是一种工具，它允许开发人员以纯文本格式编写文档(rst文档)，以便采用满足不同需求的格式轻松生成输出。例如可以将rst格式文本文档转换为html或pdf格式的文档。

安装和配置
------------------------

1. 安装sphinx::

    $ easy_install sphinx

2. 安装texlive，用于pdf转换，转换html的话不用安装::

    $ sudo apt-get install texlive-full

3. 运行 sphinx-quickstart 命令配置sphinx，使用"phoenix"作为项目名称，release按需填写，source文件与build文件分开目录存放选择yes，其他使用默认参数，生成的工作目录结构如下::

    ├── build
    ├── source
        ├── _static
        ├── _templates
        ├── conf.py
        ├── index.rst
    ├── make.bat
    └── Makefile

使用方法
------------------------

* rst文件转换到pdf

    由于sphinx工具不支持从rst格式直接转换到中文的pdf文件。所以在转换过程中需要先从rst格式转换到tex格式，通过修改tex格式文件后再转换到pdf文件，步骤如下

    1. 准备好需要转换到pdf的rst文档

    2. 修改index.rst文件，在doctree部分添加rst文档的名称，如rst文档名称为example，不带文件后缀::

        .. toctree::
            :maxdepth: 2

            example

    3. 转到工作目录下，执行命令 make latex 生成latex相关文件。例如我的工作目录为 /home/project/phoenix/sphinx，则传到工作目录后运行命令，命令会在目录 /home/project/phoenix/sphinx/_build/latex 下生成一系列文件

    4. 修改latex目录下的phoenix.tex文件，在 \begin{document} 一行之前添加一行 \usepackage{CJKutf8} ，在 \begin{document} 一行之后添加一行 \begin{CJK}{UTF8}{gkai}，然后在phoenix.tex最后的 \end{document} 一行之前添加一行 \end{CJK}::

        \usepackage{CJKutf8}
        \begin{document}
        \begin{CJK}{UTF8}{gkai}

        ...

        \end{CJK}
        \end{document}

    5. 转到latex目录下执行命令 pdflatex phoenix.tex 生成pdf文件

* rst文件转换到html

    1. 第1,2步与转换到pdf一样

    2. 转到工作目录下，执行命令 make html，命令会在目录 /home/project/phoenix/sphinx/_build/html 下生成html文件


编译方法
----------------------------

在 tools 目录下有 make-docs.py 文档编译文件，直接运行后可编译出文档