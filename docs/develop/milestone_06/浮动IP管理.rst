浮动IP管理
===================================

提供浮动IP的管理功能

前置条件
-----------------------------------

无

核心数据模型
-----------------------------------

无

页面跳转逻辑
-----------------------------------

网络管理 - 浮动IP

查看浮动IP的IP地址、已绑定云桌面、浮动IP池、使用情况, 已绑定实例的显示"已使用", 未绑定的则显示"-"

未使用的浮动IP, 可以选择与云桌面进行绑定

已使用的浮动IP, 可以选择进行解绑

可以从浮动IP池申请分配浮动IP

可以将已有浮动IP释放回浮动IP池

将OpenStack的浮动IP数据同步至本地数据库, 并且显示上次的同步时间

URL 列表 ::

    /network/floatingips                      显示浮动IP管理界面
    /network/floatingips/table                浮动IP列表采用异步加载,这里为jqeury datatables提供ajax data source
    /network/floatingips/sync                 同步浮动IP


核心业务逻辑
-----------------------------------

同步：同步任务交由Celery worker进行执行


已知问题和扩展
----------------------------------

* 同步过程交由celery执行, 而且数据库没有记录同步任务的执行情况, 所以即使同步失败, 也没有办法告知用户,

  用户仅仅能从上一次的同步时间来自己做推断, 后续待完善

* 浮动IP应该是与端口进行绑定的, 但为了简化系统逻辑, 浮动IP改为与云桌面进行绑定, 具体实现: 假设一个云桌面

  连接了3个内部网络, 也就是有3个端口, 表现为有3个固定IP, 那么在进行绑定时, 逐个对这3个端口进行绑定, 直到

  成功为止; 如果都不成功, 就返回失败


