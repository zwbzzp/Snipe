使用 JSON 进行数据提交的方法
=================================

当数据需要通过 JSON 进行提交时，如批量操作等，用 jQuery 的 ajax 方法，以及 jquery-json 插件，如 ::

    var selected_data = [1,2,3,4,5];
    $.ajax({
        url: "/students/",
        type: "DELETE",
        contentType: "application/json",
        data: $.toJSON(selected_data),
        success: <success 回调函数 >,
        error: <error 回调函数> ,
    });

注意，所有的 DELETE / POST / PUT / PATCH 操作已进行 CSRF 保护，并已写入到基础模板 `layout.html` 中。

在基础模板中，已对 jQuery 的 ajax 操作进行了全局的设置，加入了 CSRF 保护。
