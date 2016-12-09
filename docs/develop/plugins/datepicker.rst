datepicker 设置
=======================

语言文件
---------------

i18n/bootstrap-datepicker.zh-CN.js

加载方式
---------------

已在模板中加载

css::

    {% block plugin_styles %}
        <link href="{{ url_for('static', filename='css/datepicker.min.css') }}" rel="stylesheet">
    {% endblock %}

javascript::

    {% block plugin_scripts %}
        <script src="{{ url_for('static', filename='js/bootstrap-datepicker.min.js') }}"></script>
        <script src="{{ url_for('static', filename='i18n/bootstrap-datepicker.zh-CN.js') }}"></script>
    {% endblock %}

使用 ::

    <input class="date-picker">

    $(document).ready(function () {
        $(".datepicker").datepicker({
            language: "zh-CN",
            format: "yyyy-mm-dd",
            autoclose: true,
            todayHighlight: true
        });
    });

如果要附加其它图标 ::

    <div class="input-group">
        <input class="date-picker">
        <span class="input-group-addon"><i class="fa fa-calendar"></i></span>
    </div>

    $(document).ready(function () {
        $(".datepicker").datepicker({
            language: "zh-CN",
            format: "yyyy-mm-dd",
            autoclose: true,
            todayHighlight: true
        }).next().on(ace.click_event, function(){
            $(this).prev().focus();
        });
    });

已知问题
----------------

bootstrap 的 datepicker 在模态对话框中使用时，会因为 z-index 的问题导致被模态框遮住，这时，可使用一个元素 （如 div span 等）包住 input 元素，然后设置其 z-index 为 9000 ，如 ::

    <div style="z-index: 9000">
        <input type="text" class="date-picker"/>
    </div>

    <script>
        ...
        $(".date-picker").datepicker(...);
        ...
    </script>
