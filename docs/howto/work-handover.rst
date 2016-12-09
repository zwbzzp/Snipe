工作交接
==============================

个人资料
----------------------------

个人邮箱::

    huangchao@vinzor.com
    admin123

负责的工作
----------------------------

1. 管理系统

描述： 旧有管理系统的维护，包括功能添加，bug修复，配合完成测试，客户问题跟踪等

环境和工具：

    SVN 目录::

        当前1.x版本： http://172.18.231.2/svn/VinzorProject/branches/vinzor_v1
        trunc版本： http://172.18.231.2/svn/VinzorProject/trunk/vinzor
        agent1.0： http://172.18.231.2/svn/VinzorProject/branches/agent_v1.0 关于agent问题，请咨询景辉或者才哥

    openstack 测试环境::

        172.18.215.7    admin/admin123
        172.18.215.164  admin/vinzoradmin301

相关文档或资料：

    类别： 全部已有文档

    存档地址::

        ftp://222.200.185.38/Development/WEB/documents/
        账户：openstack/te$t123

手头工作：

    新功能：无

    bug 修复： 274, 277 已经修复完成，321在周洪宇手上，还没review，319参考教育版处理

    其他待解决bug： 305, 358, 360, 361

    其他(1.7功能)： Trac上面搜索属主为 huangchao，状态部位 close 的 ticket，之前有关1.7做过的相关的功能都在::

        http://172.18.231.2/svn/VinzorProject/branches/vinzorv1.7_tmp，目前只有本地代码，还未提交

    域认证：
        代码在给的 云晫代码.rar 压缩包里面的 vinzor_st 代码里， setting 里有描述认证时候用到的 backend 列表，是 django 支持的功能。具体实现在文件 ldap_backend 里，通过继承 authenticate 方法来实现。

    1.7提交的代码::

        ftp://222.200.185.38/Development/WEB/云晫代码.zip
        vinzor: 最新代码
        vinzor_fudp: 1.7部分功能，pgina 的windows版本已完成,使用的镜像是在点7上的 huangchao_pgina_shapshot_1，linux 版本还没，需要用 pam 实现， 还有 cinder 替换 samba 的功能也还没做， 用 mq 替换 task 分发的工作在周宏宇手上。
        vinzor_st: 升腾与管理系统合并后的代码

原有的工作流程：

    新功能开发：
        1. trac创建task，并分派任务
        2. 开发者accept任务
        3. 完成代码功能，将任务转为resolved
        4. resolved以后将ticket提给测试人员测试，状态为reviewed
        5. 等待测试
        6. 验证通过后由测试人员关闭ticket或者转会给开发者关闭ticket

    bug 修复：
        1. 有bug发现者或者测试人员在Trac上提bug
        2. 开发人员accept该bug
        3. 完成代码功能，将任务转为resolved
        4. resolved以后将ticket提给测试人员测试，状态为reviewed
        5. 测试通过后又测试人员关闭bug
        6. 测试不通过该bug又转给开发人员，开发人员重新accept

难点：

    新功能开发的难点：暂无

    bug 修复的难点：有的bug在使用场景上，没有一个很好的场景方案，修此失彼

建议：

    现有管理系统的问题和建议：


2. 升腾合作

描述： 管理系统和升腾云系统可取部分的整合，打造稳定的云桌面解决方案。现升腾云系统可取部分为终端和远程桌面协议

环境和工具：

    升腾与管理系统暂时融合方案的代码的svn路径::

        http://172.18.231.2/svn/VinzorProject/branches/vinzor_st

    开发用accesskey,用来调用 CDC api 时使用，会过期，过期后向升腾要新的 key::

        InBh/piTSldxG6iC6apAbw+LOcPvJ45Owq/nryHpSeKhnP4ZOJokUbRuNR0xJ2nUyBOgWUNgNBf2Y2DOTgyweDStpmH3dvTsFQpee3F9Df6pJZttLbtPMQk9zUKvL/1Rgcv42fnWknOrqp0p15nz/fcN1XuB7rkjCYn6cI41dAo=

    已经搭建好或正在搭建的测试环境::

        升腾自有的管理界面：http://172.18.228.22:8787/cdmp/
        升腾自有的用户界面：http://172.18.228.22:8787/cdp/

    升腾的物理环境地址::

        xenserver： 172.18.228.20
        dhcp: 172.18.228.21
        cdc: 172.18.228.22

    在管理界面登录后有在线的帮助文档来了解业务逻辑，其他无。
    账户Administrator:admin123

    使用到的域服务器 ip 和 域管理员账号::

        172.18.228.22
        Administrator:admin123

    搭建环境使用的产品和来源： 升腾给的

    如何搭建环境::

        部署文档见ftp://222.200.185.38/Development/WEB/%CF%EE%C4%BF%D7%A8%D3%C3/%C9%FD%CC%DA/
        使用到的技术： 未知

文档或资料：

    类别： API及安装文档

    存档地址::

        ftp://222.200.185.38/Development/WEB/%CF%EE%C4%BF%D7%A8%D3%C3/%C9%FD%CC%DA/

    文件说明::

        CDC.rar
        压缩包解压后会包含目录中的部分文件

        CdcSuitSetup-20150717.exe
        安装cdc服务，装完后就可以用cdc了

        XenCenter-6.2-XenCenter-Japanese-SimplifiedChinese.msi
        XenCenter的客户端，相当于vmware的vsphere client

        XenServer-6.2.0.iso
        XenServer的安装光盘

        Xred-license-Server-3.00-2015042901.rar
        Xred的license，过期了可以找升腾要

        升腾云桌面API餐卡奥文档_old.pdf
        升腾api的文档，最新的 api 在压缩包 CRD.rar里

        升腾桌面云部署手册，pdf
        CDC部署手册

        学生桌面。xva
        升腾给的测试vm模板

        系统管理服务器。xva
        CDC的服务器镜像，装完XenServer之后启动这个镜像，然后通过网页就能访问一个已经装好的CDC了，一般通过这个镜像去部署CDC会比较简单，手动自己去部署会比较麻烦

手头工作：

    主要负责的工作：暂无

    之前出差福州的工作内容：
    根据升腾给的rest api封装用于api调用的client，都在cloud/centerm目录下。将现有代码涉及到openstack调用的api都替换为升腾的client调用

    升腾联系人的姓名和联系方式：
        罗伟是研发领导，是钱坤和夏威的领导
        夏威是dev，比较熟悉开发部分
        钱坤: 186 5930 1821

难点：

    业务逻辑转换

建议：

    多跟升腾的人沟通。


可用人员
----------------------------

姓名: 周洪宇

以前的工作经历: 博广过来帮忙的

工作内容: 中大的业务系统开发

能力:
    概况： 良
    修复一个bug大概要用多久时间： 一天内
    bug 修复的质量如何： 大部分可用，少部分理解有问题
    是否有自己的想法： 暂无

工作态度： 良

大概掌握哪些技能和知识： 新学python，前端比较熟悉

以前分配到的工作：

    功能开发: 暂无

    bug 修复: Trac上所有VINZOREE开头的bug，已经基本完成，现在没有给新任务


姓名： 肖薇薇

以前的工作经历: 研究生

能力: 基础略差，上学期在学习代码，效果不好。分配简单任务来帮助其学习