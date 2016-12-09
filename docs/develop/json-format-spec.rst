json 交互格式规范
==============================

概述
------------------------------

管理系统在两处地方需要使用 json 作为数据交互格式，一个是管理系统页面与后端通信时，另一个是当客户端与管理系统通信时。

本规范主要是规定在使用 json 时的数据交互格式


响应格式
------------------------------

json 响应格式统一使用 JSend。JSend 规定了服务端响应的 json 格式。JSend 专注于应用程序级信息传输，是的它非常适合在 REST 风格的应用或 API 中使用。

JSend 将响应分成三种基本的类型，分别是 success, fail, error。同时指定了必要的和可选的字段：

    1. success ::

        描述：
        一切正常，并且（通常是）返回一些数据

        必要字段：
        status, data

    2. fail ::

        描述：
        提交的数据由问题，或者 api 调用的一些前提条件不满足而被拒绝。JSend 对象定义了一个用于说明出错原因的字段，通常是字段验证错误

        必要字段：
        status, data

    3. error ::

        描述：
        处理请求时出错，例如：一个异常被抛出

        必要字段：
        status, message

        可选字段：
        code, data

响应类型示例 ::

    * success 成功状态例子

        必要字段：
        1. status： 应该始终设置为 "success"。
        2. data： 提供 api 调用返回数据的包裹，如果调用没有返回数据（如最后一个例子），该字段应被设置为 null。

        ## GET/posts.json

        {
            status : "success",
            data : {
                "posts" : [
                    { "id" : 1, "title" : "A blog post", "body" : "Some useful content" },
                    { "id" : 2, "title" : "Another blog post", "body" : "More content" },
                ]
            }
        }


        ## GET /posts/2.json

        {
            status : "success",
            data : {
                "post" : { "id" : 2, "title" : "Another blog post", "body" : "More content" }
            }
        }


        ## DELETE /posts/2.json

        {
            status : "success",
            data : null
        }


    * fail 失败状态例子

        必要字段：
        1. status： 应该始终设置为 "fail"。
        2. data： 提供请求失败的具体原因描述。如果失败的原因对应 POST 值，响应对象的字段应当和这些 POST 值一一对应。

        ## POST 一个对象到后端，并且对象中没有提供 title 字段

        {
            "status" : "fail",
            "data" : { "title" : "A title is required" }
        }


    * error 失败状态例子

        必要字段：
        1. status： 应该始终设置为 "error"。
        2. message： 提供有意义的，用户易读的信息，说明出错的原因。

        可选字段：
        1. code： 错误代码
        2. data： 有关该错误的任何其他信息，例如跟踪堆栈等信息

        ## 向服务器请求 post 列表，但后台发生错误，所以返回错误和错误信息

        {
            "status" : "error",
            "message" : "Unable to communicate with database"
        }


请求格式
------------------------------

对于请求的格式，可以分几种常用场景进行说明：

1. 一个完整的数据对象的提交

    这种情况一般使用表单更加方便，但如果存在不确定的项时可能使用 json。提交对象的内部使用键值对的方式描述对象的各个属性及其对应的值，如下 ::

        {
            "id" : 1,
            "title" : "A blog post",
            "body" : "Some useful content"
        }


2. 对象列表的提交

    对象列表是一系列相同类型对象的集合，使用列表的方式描述，如下 ::

    [
        {
            "id" : 1,
            "title" : "blog post number one",
            "body" : "Some useful content of post number one"
        },
        {
            "id" : 2,
            "title" : "blog post number two",
            "body" : "Some useful content of post number two"
        }
    ]


3. id 列表的提交 ::

    一般在批量删除操作中，就会使用到 id 列表的提交。即把需要删除的对象的 id 列表提交到后台

    [
        "100001",
        "100002",
        "100003",
        "100004",
        "100005",
        "100006"
    ]
