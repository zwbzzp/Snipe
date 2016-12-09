WTForm 使用问题
=======================================

在使用 ace 框架时，有些元素在 html 展示时需要到 class / data-* 之类的属性。

在使用 wtform ，这些属性的名字不能直接写在调用时的 field 调用参数，而是需要有一点转换，如下 ::

    {{ form.name(id='course_name', class_='form-control', type='text', data_placeholder='课程名称' }}

目前， 从 html 到 wtform 支持的转换包括 ::

    data-*  -> data_*
    class   -> class_
    for    -> for_

目前不支持其它的属性，如有必要，可通过初始化时进行 monkey-patch 修改转换函数 ( wtform.widgets.core.html_params)

其它 bootstrap 中使用 data-* 方式提供接口的组件，如果中间含有 - ，那么只能通过 jquery 方式设计参数，如 ::

    <input name="start_date" class="date-picker" data-date-format="yyyy-mm-dd">
    # 需要把 data-date-format 属性转换为 jquery 中的设置
    {{ form.start_date(class_='date-picker') }}
    <script>
        $(document).ready(function() {
            $(".date-picker").datepicker({
                format: "yyyy-mm-dd",
            })
        });
    </script>
