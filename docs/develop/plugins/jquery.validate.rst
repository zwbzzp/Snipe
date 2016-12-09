jquery validation 插件使用
============================

jquery validateion 插件提供了前端数据验证框架，文档见 https://jqueryvalidation.org/documentation/

语言文件
---------------------------

i18n/jquery.validate.zh-CN.js

加载方式
---------------------------

layout.html 基础模板中加载

使用方式
---------------------------

校验定义放在 static/js/vinzor-validate.js 文件中，里面包含所有常用的检验方法

定义一个校验方法 ::

    $.validator.addMethod("方法名", function(value, element, params) {
        return this.optional(element) || <校验代码> ;
    }, "错误提示消息");

可把多个校验方法合并为一个校验类 ::

    jQuery.validator.addClassRules("name", {
          required: true,
          minlength: 2
    });

*标准方法* 通过 data-rule 方式将校验规则直接嵌入到 html 减少 javascript 代码 ::

    <input name="age" type="text" date-rule-required="true">

校验定义时建议通过内嵌到 html 代码和 CSS 的方式使用，代码更加紧凑，如 ::

    <form id="login_form">
        <input name="username" type="text" required>
        ...
    </form>

    <form id="login_form">
        <input name="username" type="text" class="name">
        ...
    </form>

或使用 metadata 方式(这种方式依赖 jquery.metadata.js ,但目前未包含在项目中) ::

    <input name="age" type="text" class="{required:true, digits:true}">

然后在提交检查时，使用以下的 jquery 代码 ::

    $("#login_form").validate()
    if ($("#login_form").valid()) {
        ....
    }

错误消息的位置用 errorPlacement 参数，它会改变默认的错误消息位置，如 ::

    $(currentLessonForm).validate({
        errorPlacement: function (error, element) {
            if ($(element).hasClass('date-picker') || $(element).hasClass('time-picker')) {
                error.insertAfter($(element).parent());
            } else {
                error.insertAfter(element);
            }
        }}
    );

在对select2控件进行校验，需要定义ignore的值，不能让ignore为默认，否则将不进行校验。如果要在select2中设置校验条件满足后错误消息自动隐藏，需要手动修改错误消息为空。
例如 src/web/app/templates/storage/personal_account.html：

    <select id="add_samba" class="select2" name="samba" data-placeholder="请选择" style="width: 100%;" data-rule-required="true" data-msg-required='请选择samba服务器'>
        <option value=""></option>
        {% for samba in samba_list %}
            <option value="{{samba.id}}">{{samba.name}}</option>
        {% endfor %}
    </select>

    //ignore中需要定义为空而不能保持默认值，否则select2控件不进行校验
    var $new_validator = $("#new_form").validate({
        ignore:''
    });

    //当满足校验条件后修改错误消息为空
    $("#add_samba").change(function(){
        $new_validator.showErrors({samba:""});
    });

