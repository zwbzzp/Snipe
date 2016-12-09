phoenix 重构项目
================

phoenix 的目标是整理和重构云晫业务管理系统，把系统中的领域模型、业务规则整理清楚，为后期的扩展、维护打下基础。

与原管理系统的目标类型， phoenix 在 openstack 的基础上提供云计算服务。

在底层，除 openstack 所提供的功能外， phoenix 额外增加服务器管理和部署、动态扩容、服务器迁移等与云计算紧密相关的功能。 phoenix 在虚拟化基础设施管理层面，完善 openstack dashboard 的不足，总结之前的使用经验，把在 api 层面提供的部分功能补充进来。

在业务逻辑层面的修改最多，需要把管理系统原来散乱的业务逻辑关系重新理清，并强化业务概念和业务目标，建立稳定的核心业务领域模型。在此基础上，针对不同的行业应用目标，在此基础上进行定制开发。


层次和划分
---------------

1. L0: 物理设施和物理设施的管理
    管理物理服务器、网络、存储等物理设施，实现自动部署、物理资源监控、扩容、迁移等操作。

2. L1: 虚拟化基础设施和管理
    围绕虚拟化基础的概念，如 vm 、网络、存储等，完善 openstack 的 dashboard，根据之前的使用经验，逐步增强功能。

3. L2: 核心业务逻辑、业务规则
    在虚拟化的基础上，根据业务的实际需要，以桌面为核心，建立云桌面领域模型和业务规则库。

    L2 层进行业务层面的配额管理，L2 只针对到单一的 tenant。

4. L3：行业规则（教育、办公、云主机）
    针对不同行业，进行顶层功能定制。


目录结构
---------------

目录结构和说明如下::

    /docs   文档
        /develop    开发文档
        /howto      辅助文档
        /manual     用户手册
    /infras         docker 设施
    /src
        /phoenix    主源码
        /tests      单元测试代码
    /tools          辅助脚本或工具
    .gitignore      git 自动忽略文件
    README.rst      项目简介
    requirements.txt        主要依赖
    requirements-docs.txt   文档依赖
    requirements-test.txt   测试依赖

如何开始
---------------

1. 学习项目管理指南
    从 seafile 上下载项目管理指南，学习 git gitlab git-flow 的使用，seafile 的地址为 `http://seafile.vinzor.org/ <http://seafile.vinzor.org/>`_ 。

2. 下载源代码
    开通 gitlab 账户，登录到 gitlab `http://172.18.231.4:8080/vinzor/phoenix/ <http://172.18.231.4:8080/vinzor/phoenix/>`_ 。

    然后，设置自己的 ssh 密钥，并根据项目管理指南的指引，下载源代码。

3. 设置开发环境
    开发环境设置参照 docs/howto 系列文档



