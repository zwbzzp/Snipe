如何添加定制的 jinja filter
==============================

概述
------------------------------

flask 使用 jinja2 作为默认模板引擎，但是 flask 提供的 jinja filter 有限，开发人员有时候需要定制 filter

如何定义 jinja filter
------------------------------

项目的定制 jinja filter 统一定义在 /phoenix/src/web/app/jinja_filters.py 文件下。 在 flask app 启动时会扫描并加载 jinja_filter.py 里的 filter。 具体定义语法如下::

    def datetime_format(value, format='yyyy-MM-dd hh:mm'):
        """Formats a date time according to the given format."""
        if value in (None, ''):
            return ''
        try:
            return dates.format_datetime(value, format)
        except AttributeError as ex:
            return ''


如何使用定制的 jinja filter
------------------------------

使用方法和使用 flask 默认提供的 filter 相同。 例如在模板里使用以上定义的 datetime_format：：

    <input type="text" value="{{ mydatetime|datetime_format(''hh:mm'') }} />
