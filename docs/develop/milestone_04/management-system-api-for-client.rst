客户端调用的管理系统 API
===========================

概述
---------------------------
客户端是一个安装在瘦终端的应用程序，用于与管理系统连接并获取虚拟桌面，使得用户可以在瘦终端使用虚拟桌面。

客户端与管理系统的通信接口由管理系统提供，是一套 RESTful 风格的 api


api 改造 目标
---------------------------

原有客户端 api 存在的问题：

1. 原有客户端使用的 api 与管理系统页面的 api 混合使用，这使得原来的客户端 api 存在一些问题：

    1. 与页面 api 耦合在一起，页面 api 的更改会影响客户端的使用
    2. 由于页面 api 用于处理 web 请求，返回的结果中包含大量 html，js等信息，这对于客户端来说是无用的

2. 原有的客户端 api 某些端点定义不清晰，需要重新梳理重新定义


改造的目标是：

1. 将客户端 api 从原有的 管理系统页面 api 中分离出来，客户端使用一套独立的 api

2. 定义功能清晰的 RESTful api

3. 对原有 api 的具体实现重新梳理并重写


旧有 api 定义
---------------------------

原有 api ::

    /login
    名字上是用于登陆，但实质上是用于获取管理系统端的 csrf token，看是否可以移除这个接口，与登陆接口合并
    新 api 不使用 crsf token， 废弃这个 api

    /login_result
    真正的登陆接口，登陆时携带 /login 接口获取到的 csrf token 和用户名，密码一起发送到管理系统，验证登陆
    新 api 不需要用户登陆，每次请求需要提供 credential （用户名密码或 token）

    /admin_login
    管理员使用的专用登陆接口，看是否可以与普通登陆接口 /login_result 合并
    新 api 不需要用户登陆，每次请求需要提供 credential （用户名密码或 token）

    /logout
    用户登出接口，据说客户端会调用此接口，查看后端实现具体执行了哪些操作(销毁 session?)
    新 api 不使用 cookie，所以不需要登出系统来使 cookie 过期

    /change_own_password
    修改密码，据说是因为学生一般只通过客户端登陆，在客户端提供这个接口可以方便学生修改密码

    /heart_beat
    检测管理系统的心跳，原有接口实现据说会出现心跳失灵，即管理系统会话已经超时失效，在请求虚拟机时(request_vms)本该返回错误代码666给客户端，但却返回代码200，并返回空的虚拟机列表
    愿意是想通过这个 api 来维持本地 cookie 不过期，新 api 不使用 cookie，所以需要心跳，可以废弃

    /request_vms
    获取该登陆用户的虚拟机列表

    /resume_vm
    唤醒指定的虚拟机

    /poweroff_vm
    关闭指定的虚拟机

    /reboot_vm
    重启指定的虚拟机

    提示： 以上 api 除了 /login 和 /heart_beat 之外，其他的 api 调用都需要客户端的请求中包含 csrf token，否则管理系统的返回结果将会是重定向


新版本 api 定义
---------------------------

* api 使用方法

    1. 客户端首先通过 /api/v1.0/token 获取临时 token，具体方法是把 request 中的 Authorization 设置为用户名和密码的值，格式为 username:password
    
    2. 在之后的其他所有请求中就使用 token 用于用户验证，具体方法是把 request 中的 Authorization 设置为 token 的值
    
    3. 每个获取到的 token 会在一定时间后过期（默认2小时），所以客户端可以在 token 过期之前主动地再次获取新的 token，或者在 token 过期服务器验证失败后再次请求新的 token


* 新版本的 api 遵循 restful 风格，其中以下以下几点需要提醒：

    1. 引入 api 版本到 url 中，如 /api/v1.x
    
    2. 针对某个登陆用户的行为使用速记 me 代替用户 id，如 /users/me/xxx，其中 xxx 为针对该用户的行为
    
    3. 虚拟机的行为使用 /api/v1.0/desktops/<string:id>/action， 并使用 POST 方法在发送 body 里指定具体操作，如重启虚拟机 ::
    
        {
            'reboot': null
        }
    
    4. 返回的响应统一使用 JSend 里描述的返回格式，如下，返回状态有三种类型，分别是 success, fail, error，具体看考资料 https://labs.omniti.com/labs/jsend ::
    
        * 请求成功
    
        {
            status : "success",
            data : {
                "post" : { "id" : 1, "title" : "A blog post", "body" : "Some useful content" }
             }
        }
    
        或者
    
        {
            status : "success",
            data : null
        }
    
    
        * 请求失败
    
        {
            "status" : "fail",
            "data" : { "title" : "A title is required" }
        }
    
    
        * 请求发生服务器端错误,其中 code 和 data 为可选的 key
    
        {
            "status" : "error",
            "message" : "Unable to communicate with database",
            "code": “123”,
            "data": “data describe errors”
        }

    5. 调用 api 的用户有三种类型，分别如下（星号列表为该类型用户的特点） ::

        1. 普通用户：

            * 请求中需要提供用户名和密码

            * 调用 api 时候需要检查权限

        2. 管理员：

            * 请求中需要提供用户名和密码

            * 可以调用全部 api， 且根据调用请求中标识的调用模式来确定是否忽略管理系统中对 api 调用的限制.
              例如， 调用 /api/v1.0/terminals/registration 注册终端时， 若请求中的 mode （模式）为 'auth'，
              'auth' 模式即直接通过终端注册， 不需要管理系统的干预， 同时也忽略掉管理系统系统设置中预先设置的 "终端注册模式"。

        3. 匿名用户：

            * 请求中不需要提供用户名和密码

            * 调用 api 时候需要检查权限。一般匿名用户只能调用部分查询 api

* 新版本 api 定义::

    1. 用户类

        1. 修改本用户密码
            Operation
                GET /api/v1.0/users/me/reset_password

            Request：对虚拟桌面的操作类型
                Property
                    password

                Sample
                    {
                        'password': 'admin123'
                    }

            Response: 返回操作结果
                Property
                    status
                    data

                Sample
                    {
                        status : 'success',
                        data : null
                    }

        2. 获取用户临时 token
            Operation
                GET /api/v1.0/token

            Request：请求头部 Authorization 提供用户名和密码
                Sample
                    Authorization: Basic username:password

            Response: 服务端新生成的 token， 其中 "token" 下的 "id" 为新生成的 token 字符串， "issued_at" 为 token 生成的时间，"expires" 为 token 过期时间，时间格式统一使用 iso8601
                Property
                    token

                Sample
                    {
                        status : 'success',
                        data : {
                            'token' : {
                                'id': 'thisisatoken'
                                'issued_at': '2016-03-04T21:08:12',
                                'expires': '2016-03-04T23:08:12
                         }
                    }

    2. 虚拟机操作类

        1. 获取用户的虚拟机列表
            Operation
                GET /api/v1.0/users/me/desktops

            Response: 用户的虚拟桌面列表和网关列表（现在只支持课程桌面，还不支持网关）
                Property
                    desktop_list
                    gateway_list

                Sample
                    {
                        status : 'success',
                        data : {
                            'desktop_list': [
                                {
                                    'id'： '123456789',
                                    ‘name’: 'mydesktop',
                                    'status': 'ACTIVE',
                                    'os_username': 'fake_username',
                                    'os_password': 'fake_password',
                                    ‘default_connection_type’: 'rdp',
                                    'policy': {
                                        'enable_usb': True,
                                        'enable_clipboard': True,
                                        'enable_audio': True
                                    },
                                    'connection_info': [
                                        {
                                            'type': 'rdp',
                                            'ip': '192.168.1.10'
                                        },
                                        {
                                            'type': 'spice',
                                            'ip': '192.168.1.10',
                                            'port': '5678'
                                        }
                                    ]
                                }
                            ],
                            'gateway_list': []
                         }
                    }


        2. 唤醒指定的虚拟机
            Operation
                POST /api/v1.0/desktops/<string:id>/action

            Request：对虚拟桌面的操作类型
                Property
                    action

                Sample
                    {
                        'resume': null
                    }

            Response: 返回操作结果
                Property
                    status
                    data

                Sample
                    {
                        status : 'success',
                        data : null
                    }


        3. 重启指定的虚拟机
            Operation
                POST /api/v1.0/desktops/<string:id>/action

            Request：对虚拟桌面的操作类型
                Property
                    action

                Sample
                    {
                        'reboot': null
                    }

            Response: 返回操作结果
                Property
                    status
                    data

                Sample
                    {
                        status : 'success',
                        data : null
                    }


        4. 关闭指定的虚拟机
            Operation
                POST /api/v1.0/desktops/<string:id>/action

            Request：对虚拟桌面的操作类型
                Property
                    action

                Sample
                    {
                        'shutdown': null
                    }

            Response: 返回操作结果
                Property
                    status
                    data

                Sample
                    {
                        status : 'success',
                        data : null
                    }


        5. 返回课时列表(此 api 无需用户验证)
            Operation
                GET /api/v1.0/places

            Response: 返回操作结果
                Property
                    status
                    data

                Sample
                    {
                        status : 'success',
                        data :
                        {
                            'place_list':[
                                {
                                    'name':'b101',
                                    'address':'one floor'
                                },
                                {
                                    'name':'b201',
                                    'address':'two floor'
                                }
                            ]
                        }
                    }

        6. 验证是否为系统管理员
            Operation
                GET /api/v1.0/users/me/is_administrator

            Response: 返回操作结果
                Property
                    status
                    data

                Sample
                    {
                        status : 'success',
                        data : 'true'
                    }


        7. 根据mac地址返回终端信息(此 api 暂时无需用户验证)
            Operation
                GET /api/v1.0/terminals/<string:mac_address>

            Response: 返回操作结果
                Property
                    status
                    data

                Sample
                    * 成功
                    {
                        status : 'success',
                        data :
                        {
                            'place': 'b101',
                            'seat_number': '01',
                            'mac_address': '08:00:20:0A:8C:6D',

                            # 返回的终端状态有三种：
                            # 1. APPROVIED: 终端已经通过注册
                            # 2. WAITING: 终端正在等待审批
                            # 3. REJECTED: 终端的注册申请被拒绝
                            'state': 'APPROVED'/'WAITING'/'REJECTED'
                        }
                    }

                    * 失败，终端不存在
                    {
                        status : 'fail',
                        data : 'terminal not exist'
                    }


        8. 申请注册终端(此 api 暂时无需用户验证)
            Operation
                POST /api/v1.0/terminals/registration

            Request：对虚拟桌面的操作类型
                Property
                    place
                    seat_number
                    mac_address
                    mode # optional

                Sample
                    {
                        'place': 'b101',
                        'seat_number': '01',
                        'mac_address': '08:00:20:0A:8C:6D',

                        # if mode is 'auth', register terminal directly, despite management system settings.
                        # otherwise, register process will go on according to management system settings.
                        # 若 mode 为 auth，则说明此次注册是由管理员在客户端发起的，
                        # 则终端会忽略管理系统端系统设置中的"终端注册模式"选项，直接让终端注册成功，
                        # 若不提供 mode 参数，则说明此次注册不是由管理员发起的，
                        # 则需要按照管理系统端系统设置中的"终端注册模式"进行终端注册流程。
                        # 提供 auth 参数需要同时提供管理员的用户名和密码，否则无效
                        'mode': 'auth'
                    }

            Response: 返回操作结果
                Property
                    status
                    data

                Sample
                    * 成功
                    {
                        status : 'success',
                        data :
                        {
                            ‘terminal_state’: 'APPROVED'/'WAITING'/'REJECTED'
                        }
                    }

                    * 失败，终端已存在
                    {
                        status: 'fail',
                        data: 'terminal existed'
                    }

                    * 失败，课室和座位号已经存在
                    {
                        status: 'fail',
                        data: 'place and seat number existed'
                    }

                    * 失败，终端注册参数格式不正确，errors 是错误列表
                    {
                        status: 'fail',
                        data: {
                            ‘errors’: ['place': 'error messages here']
                        }
                    }