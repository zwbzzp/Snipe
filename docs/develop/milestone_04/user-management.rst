用户管理页面设计
===========================

概述
---------------------------
本系统的用户管理与通常我们看到的系统里的用户管理功能相当，主要实现用户的创建，修改，查看和删除功能。

但是本系统的用户管理在用户角色方面作了一点简化，就是根据业务的需要，只预定义了三种用户角色，分别是管理员，教师，学生。

所以在用户管理的页面上会显示三个页面，分别对应以上三种用户角色，在不用页面创建的用户会被赋予该页面所负责角色的权限。


页面结构
---------------------------

页面结构如下 ::

    ├── 用户管理
        ├── 管理员
        ├── 教师
        ├── 学生


页面功能
---------------------------

管理员页面：

    1. 用户列表，分页显示，查询用户

    2. 创建，修改，删除指定用户

    3. 批量删除用户

    4. 禁用指定用户

教师页面：

    1. 用户列表，分页显示，查询用户

    2. 创建，修改，删除指定用户

    3. 批量删除用户

    4. 禁用指定用户

    5. 下载用来批量导入用户的用户信息模板

    6. 批量导入用户

    7. 导出用户列表，导出文件为 excel 格式

学生页面：

    1. 与教师页面功能相同

    2. 批量重置用户密码


实现技术
---------------------------

jquery datatable 用于展现用户列表数据，可分页数据和查询数据

    1. 具体使用方法参考课程管理

    2. 中文支持，参考文档 docs/develop/jquery.dataTables-language.rst


wtfrom 用于创建用户时数据的录入和提交

    1. 具体使用方法参考课程管理


原管理系统参考代码

原页面路径： vinzor_v1/templates/vinzor/html/account/

后端处理逻辑： vinzor_v1/module/account/


