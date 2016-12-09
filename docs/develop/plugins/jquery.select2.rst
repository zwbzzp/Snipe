select2 插件设置
=========================

语言文件
---------------

i18n/select2.zh-CN.js

加载方式
---------------

css ::

    {% block plugin_styles %}
        <link href="{{ url_for('static', filename='css/select2.min.css') }}" rel="stylesheet">
    {% endblock %}

javascript ::

    {% block plugin_scripts %}
        <script src="{{ url_for('static', filename='js/select2.min.js') }}"></script>
        <script src="{{ url_for('static', filename='i18n/select2.zh-CN.js') }}"></script>
    {% endblock %}

初始化 ::

    $(document).ready(function () {
        $('.select2').select2({
                language:'zh-CN',
                allowClear: true
            });
    }
