日志风格指南
==============================

概述
------------------------------

日志记录系统状态、业务状态、数据变化、内部错误，用于协助问题调试、错误定位、跟踪系统性能等。

日志使用
------------------------------

管理系统统一使用 python 标准日志接口，并在配置中已设置日志格式，在 python 文件代码开头处使用以下方式引入日志 ::

    import logging

    LOG = logging.getLogger(__name__)

以下的几种情况下需要插入日志：

#. 数据操作
    对数据进行任务的 CRUD 操作需要记录日志，创建和删除时级别为 info ，更新时一般使用 debug， 如 ::

        User user = User(name='test', password='test')
        db.session.add(user)
        db.session.commit()
        LOG.info('Create user %r' % user)

#. 关键系统调用
    关键系统调用中，对于调用入口处使用 info 记录（危险操作使用 warning ），其它地方用 debug 辅助调试，如 ::

        def poweroff(desktop_id):
            LOG.warning('Power off desktop %s' % desktop id)
            # more

#. 异常处理
    异常处理都使用 exception 级别记录日志（会同时记录调用栈），如 ::

        try:
            do_something()
        exception NetworkError as ex:
            LOG.exception('Could not connect server')
            # more

日志消息格式
------------------------------

日志消息需要表明大致的问题，如 ::

    Could not connect server
    Could not find xxx

