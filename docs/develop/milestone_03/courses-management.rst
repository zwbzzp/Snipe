gi课程管理功能
=================================

目标使用者：管理员、老师

使用此管理，进行课程 CRUD 操作。导入或手工增加课程上课名单（或课室，系统自动增加名单）。可启动课程、关闭课程。

查看课程的 vm ，并手工增加或删除 vm 。绑定 vm 到名单上的用户，或解除绑定关系。

核心数据模型
----------------------------------

课程 course ::

    name    课程名称
    start_date  开始日期，如2015/12/11
    end_date    结束日期，如2016/3/1
    capacity    人数
    
    image_ref   镜像id，默认的id 
    flavor_ref  配置id
    network_ref 网络id

课时 lesson ::

    course_id   课程id delete-cacade
    
    start_date          课程开始日期 index
    start_period_id     开始时间段id，引用时间表
    start_time          课程开始时间不引用时间表

    end_date            课程结束日期 index
    end_period_id       结束时间段id，引用时间表
    end_time            课程结束时间不引用时间表

    start_datetime      课程开始时间
    end_datetime        课程结束时间
    
    为支持手工调整课程时间，以及让一个课时跨越多天，使用 start_date start_time 和 end_date end_time 组合
    手工调整后，应同时清除和引用时间表相关信息

时间表 period ::
    
    name    时间段名称

    start_time      时间段开始时间
    end_time        时间段结束时间

选课表 course_selections ::

    course_id   课程id
    user_id     学生id


页面跳转逻辑
----------------------------------

课程列表 -> 点击课程 或 编辑课程 -> 课程详细信息

课程详细信息中，显示以下内容:

#. 列出课程的具体情况
#. 本周的课时分布情况
#. 选课学生名单

URL 列表 ::

    /courses        课程列表
    /courses/       创建课程 GET / POST
    /courses/<id>   课程详细信息 GET / POST / DELETE

    /courses/<id>/lessons   课程列表 GET

    /courses/<id>/students  学生列表 GET
    /courses/<id>/students/ 学生列表  POST json 上传学生名单 / DELETE json 删除
    /courses/<id>/students/<user_id>    操作单个学生 POST 添加 /  DELETE 删除


核心业务逻辑
----------------------------------


已知问题、扩展
---------------------------------

