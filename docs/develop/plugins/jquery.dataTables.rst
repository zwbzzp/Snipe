jquery.dataTables 设置
============================================

语言文件
----------------

i18n/jquery.dataTables.json

加载方式
----------------

css::

    无

javascript::

    {% block plugin_scripts %}
        <script src="{{ url_for('static', filename='js/jquery.dataTables.min.js') }}"></script>
        <script src="{{ url_for('static', filename='js/jquery.dataTables.bootstrap.min.js') }}"></script>
    {% endblock %}

jquery.dataTables 默认的语言为英文，如果需要设置为中文，则在初始化时，使用以下的代码 ::

    $(".dataTable").dataTable({
        "language":{
            "url":"{{ url_for('static', filename='i18n/jquery.dataTables.json') }}"}})
    });
