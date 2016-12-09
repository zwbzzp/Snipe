用户、角色和权限模型
=============================

用户 ::

    id              id
    username        用户名（学生编号、老师编号等自编号应用 username 表示）
    password_hash   密码 hash
    email           邮箱
    fullname        用户姓名（额外的用户名字，考虑用 profile 表进一步表示更加详细的信息）
    role_id         角色 id
    confirmed       用户是否已被确认，未被管理员或系统确认的用户将无法使用
    last_access     用户上次访问时间

角色 ::

    id              id
    rolename        角色名
    description     角色描述

权限 ::

    id              id
    name            权限名
    description     权限描述


初始化数据
-------------------------------

除模型外，需要提供初始化数据以保证系统在第一次启动时能正确运行，并有测试数据供测试使用

角色 ::

    Teacher  Student  Administrator

用户 ::

    批量创建一些用户
