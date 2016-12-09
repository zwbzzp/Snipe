基本 URL 规范
================

参考页面流程
----------------

管理系统的页面一般结构为 ::

    功能目录
     |- 功能入口 -- 列表/概要页 （创建、删除等操作，以及一些快捷更新操作）
                       |- 详情页

资源的创建两种方式，复杂资源使用单独的资源创建页，简单资源创建使用对话框

RESTful 风格 URL
-----------------
管理系统的 URL 端点在设计时，为提高兼容性和稳定性，应遵守一般的 RESTful 风格。

以 ticket 为例，使用以下的规则建立 URL ::

    GET /tickets        ticket 列表
    GET /tickets/       创建 ticket 的页面
    GET /tickets/1      获取 id 为 1 的 ticket
    POST /tickets/      创建一个新的 ticket
    POST /tickets/1     更新 id 为 1 的 ticket （或使用 PUT PATCH）
    DELETE /tickets/1   删除 id 为 1 的 ticket （浏览器不支持 DELETE 时通过 POST 和 _method 参数指定为 DELETE）

当处理关联关系的资源时，使用以下的规则 ::

    GET /tickets/1/messages     获取关联的所有 message
    GET /tickets/1/messages/1   获取关联的 id 为 1 的 message
    POST /tickets/1/messages/   创建关联的 message
    POST /tickets/1/messages/1  更新关联的 id 为 1 的 message
    DELETE /tickets/1/messages/1    删除关联的 id 为 1 的 message

资源操作(如启动、关闭)本身也表示为一个资源，使用类命令模式 ::

    POST /desktops/1/actions/

action 被记录到资源相关的 actions 表，作为审计依据