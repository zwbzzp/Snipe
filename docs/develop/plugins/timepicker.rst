timepicker 设置
=======================

语言文件
---------------

i18n/bootstrap-datepicker.zh-CN.js

加载方式
---------------

css::

    {% block plugin_styles %}
        <link href="{{ url_for('static', filename='css/bootstrap-timepicker.min.css') }}" rel="stylesheet">
    {% endblock %}

javascript::

    {% block plugin_scripts %}
        <script src="{{ url_for('static', filename='js/bootstrap-timepicker.min.js') }}"></script>
    {% endblock %}

初始化 ::

    $('.time-picker').timepicker({
        minuteStep: 1,
        showSeconds: false,
        showMeridian: false
    }).on(ace.click_event, function(){
        $(".bootstrap-timepicker-widget").css("z-index", "9999");
    }).next().on(ace.click_event, function(){
        $(this).prev().focus();
    });

已知问题
----------------

bootstrap 的 timepicker 在模态对话框中使用时，会因为 z-index 的问题导致被模态框遮住，但使用一个元素 （如 div span 等）包住 input 元素，然后设置其 z-index 为 9000，的办法
对于 timepicker 来说不生效。因此，需要在 timepicker 初始化完成后注册控件的点击事件，并在点击事件发生时动态地设置时间控件的 z-index，如下 ::

    $('.time-picker').timepicker({
        minuteStep: 1,
        showSeconds: false,
        showMeridian: false
    }).on(ace.click_event, function(){
        $(".bootstrap-timepicker-widget").css("z-index", "9999");
    }).next().on(ace.click_event, function(){
        $(this).prev().focus();
    });
