页面布局说明
====================================

web 页面采用 bootstrap + jquery + ace 框架。

ace 框架是之前的管理系统所采用的框架，基本的内容差不多，由于 bootstrap 和 ace 框架的版本升级，会有一些增强的内容。

增加的内容包括：

1. 从 bootstrap2 升级到 bootstrap3，由于2和3之间存在不兼容的情况，会存在较大差异
2. 新增加了一些参考组件

布局结构
-----------------------------------

布局的结构分为：顶部导航栏、主内容区

主内容区又区分为：侧边导航栏、内容区


扩展方法
-----------------------------------

页面应该继承 `layout.html`

提供以下几个扩展点 ::

    {% block title %}{% endblock %} 页面标题
    {% block plugin_styles %}{% endblock %} 加载插件的 css
    {% block inline_styles %}{% endblock %} 加载当前页面特定的 css
    {% block page_content %}{% endblock %}  当前页面内容
    {% block plugin_scripts %}{% endblock %} 加载插件相关的 javascript
    {% block inline_scripts %}{% endblock %} 加载当前页面特定的 javascript

如激活指定的侧边栏 ::

    {% block inline_scripts %}
        <script>active_sidebar("#dashboard")</script>
    {% endblock %}
