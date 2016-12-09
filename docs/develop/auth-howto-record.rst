auth how to
===========================

密码
---------------------------
User 模型里添加几个和密码认证的方法 ::

    password
    verify_password


flask-login
---------------------------
flask-login 要求 User 实现几个方法，替代方案为添加 UserMixin ::

    is_authenticated
    is_active
    is_anonymous
    get_id

在 app/__init__.py 里初始化 flask-login

实现回调函数返回 User ::

    @login_manager.user_loader
    def load_user(user_id):
        return ...

保护路由(TODO) ::

    @login_required

实现登陆模板 ::

    提示: current_user 由 flask-login 提供，可以在模板里直接使用，is_authenticated 函数返回 True 则用户已经登陆，返回 False 则未登陆

实现登陆路由和登陆view ::

    1. 获取登陆名，密码和记住我
    2. 检查是否存在该用户和验证用户密码
    3. 通过验证则登陆用户，使用 login_user(user, remember_me)， 该函数标记用户回话为以登陆
    4. redirect 到 next_url 或 index

登出用户路由和登出view ::

    logout_user

注册用户（not use）
---------------------------

创建用户注册表单，其中包含字段的验证函数 validate_xxx

创建用户注册模板

创建用户注册路由和注册 view


确认账户(not use)
---------------------------

生成 http://www.xxx.com/auth/confirm/<id> 之类的链接让用户点击并在后台代码认证，使用令牌代理 url 中的 id

有了以上生成的 url 后，就可以发送确认邮件

在账户确认之前可以使用入戏如下装饰器拦截请求 ::

    @auth.before_app_request


创建角色和为角色绑定权限
---------------------------

* 创建角色模型(添加 permission 关联)

预定义权限

在角色模型里预订已一些角色并绑定权限


赋予角色
---------------------------

创建用户的时候赋予角色，使用 role 作为参数传入构造函数，假如创建用户时候没有指定角色，则会分配管理员或者默认角色给用户


验证角色
---------------------------

在 User 模型里添加 can(self, permissions) 和 is_administrator(self) 函数，分别判断用户是否有参数中的权限和是否为管理员角色

添加匿名用户 AnonymousUser 模型，继承自 flask-login 的 AnonymousUserMixin，用户未登陆时会的 current_user 会被设成这个值

* 创建装饰器 permission_required(permission) 和 admin_required(f) 来装饰 view 函数，以确定用户是否有权限执行该 view 函数

为了在模板中都可以默认访问到 Permission 模型，把 Permission 加入模板上下文，使用 ：：

    @main.app_context_processor






