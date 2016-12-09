CSRF 保护
============================

为保护表单提交所造成的问题,需要使用 csrf token 保护 POST / PUT / DELETE 等需要修改数据的请求


编程模式
-------------------

前端
~~~~~~~~~~

使用 flask-wtf 的 csrf 特性统一保护所有的表单提交,并在 layout 中添加全局的 crsf meta ::

    <meta name="csrf-token" content="{{ csrf_token() }}">

如果在表单中使用时,可使用 wtform 自带的::

    {{ form.csrf_protect }}

如果在 javascript 中使用,可通过使用 meta 或直接通过注入一个 ::

    var csrftoken = $('meta[name=csrf-token]').attr('content')
    或
    <script type="text/javascript">
        var csrftoken = "{{ csrf_token() }}"
    </script>

然后,在 ajax 请求时,使用 ::

    $.ajaxSetup({
        beforeSend: function(xhr, settings) {
            if (!/^(GET|HEAD|OPTIONS|TRACE)$/i.test(settings.type)) {
                xhr.setRequestHeader("X-CSRFToken", csrftoken)
            }
        }
    });

* 以上代码已加入到 `layout.html` 中,不需要再另外设置 *

后端
~~~~~~~~~~

后端的 view 如果全部使用 csrf token 保护.如果某个视图不需要 CSRF ,那么可直接使用装饰器取消保护 ::

    @csrf.exempt
    @app.route('/courses/<id>/students/', methods=['POST'])
    def upload_student_file():
        # do something
