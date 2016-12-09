oslo.config 使用
============================

oslo.config 模块来自 openstack 的 oslo 子项目，提供一个良好的配置管理和加载库。

phoenix 使用 oslo.config 管理配置，并进行配置方面的约定。


配置代码的位置
----------------------------

配置的代码应写在模块的 `__init__.py` 文件中，如果模块只包含一个文件，那么应在 `import` 之后立即定义配置代码。


配置代码的参考形式
----------------------------
samb
配置代码参考如下 ::

    # 引入 oslo 库
    import oslo_config.cfg as cfg

    # 定义选项
    db_options = [
    cfg.StrOpt('connection', required=True,
               help='The sqlalchemy connection string'),
    cfg.IntOpt('pool_recycle', default=3600,
               help='Seconds before idle sql connections are reaped'),
    cfg.IntOpt('pool_timeout', default=30,
               help='Seconds before giving up on getting a connection from the pool'),
    cfg.IntOpt('min_poolsize', default=1,
               help='Minimum number of connections to keep opened in a session'),
    cfg.IntOpt('max_poolsize', default=10,
               help='Maximum number of connections to keep opened in a session'),
    cfg.IntOpt('max_overflow', default=None,
               help='If set, use this value for max_overflow with sqlalchemy'),
    ]

    # 注册到 cfg.CONF
    cfg.CONF.register_opts(db_options, group='database')

