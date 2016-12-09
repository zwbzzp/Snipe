调度设计
==========================

调度目的和设计目标
-----------------------

为支持在特定时间执行某些操作，以及在后台执行时间较长的任务，需要使用调度系统。

调度系统的执行包括：后台任务，定时任务

定时任务包括：

按照上课时间定时启动课程（教育行业），定时关闭 vm （按照课程配置的关闭策略）

需要支持的特性：

可管理的后台任务，支持后台任务监控

支持调度管理，当调度失败时可重启调度

基础框架
-------------------

使用 celery 的 beat 来作为定时调度，worker 执行后台任务。

通过 celery 的 events 来实时监控后台任务的工作状态。

调度工作流程
--------------------

前提条件：课程已定义好，并且已添加了上课时间。

原调度逻辑
~~~~~~~~~~~~~~~~~~~

原调度逻辑基于 APScheduler ，使用多个调度器，把任务保存在数据库中，定期读取数据库协调调度动作。

使用的调度器包括：

CourseScheduler ::

    课程调度器，job 包括：
    __init_course_task  cron        配置的晚上时间，读取当天课程的启动信息，并生成桌面调度任务
    __start_desktop     interval    配置的时间间隔，执行启动桌面操作
    __stop_desktop      interval    配置的时间间隔，执行关闭桌面操作
    __del_desktop       cron        配置的晚上时间，删除代替的课程桌面
    __del_temporary_course cron     配置的晚上时间，删除临时的课程桌面
    __notify_desktop    cron        以 0-23 */1 的方式间隔调度，通知将要回收的桌面

TaskScheduler ::

    虚拟机任务调度器，job 包括：
    __task_job          interval    配置时间间隔，检查未做的任务，然后创建线程执行
    clean_job           cron        在 星期五 23 59 59 执行，清理任务记录

IPAllocatorScheduler ::

    进行 IP 分配

FUDPScheduler ::

    自由上机，job 包括：
    fudp_add_job        cron        0-21 */1
    fudp_del_all_job    cron        删除所有自由上机桌面，增加 delete 任务
    fudp_del_job        cron        
    fudp_del_job1       cron        删除无人使用的自由桌面

DetectScheduler ::

    VM 检测调度

VM 生命周期和操作流程 ::

    CourseScheduler线程      FUDPScheduler线程
    __init_course_task       fudp_add_job
        |_______创建任务__________|
                  |
                 DB     <___更新任务 error+1 _如果超过 error 限制，创建删除任务-
                 |                                         |                    |
            TaskScheduler 读取任务 --创建并等待超时失败----|--超过 error 限制 --|
                             |_______创建，成功
                             |_______删除

调度的整理和改进
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
上课开始，课程的过程 ::

    使用桌面任务为全过程中的共享跟踪记录，任务的状态包括：
        PENDING 等待中
        RUNNING 运行中，至少一个处理器正在处理这个任务
        FINISHED 已结束
    任务的处理器负责一个任务阶段的处理：
        BUILD 创建VM
        WAIT 等待到 vm 某个状态，如 active
        ASSIGNFLOATING 分配 floating ip
        DETECT 检测 VM ，udp/ping
        RELEASEFLOATING 释放 floating ip
        SHUTDOWN 关闭 VM
        DELETE 删除 VM
        START 启动 VM
    任务中记录一个处理链，通过 next_stage / prev_stage 获取，提供一个 context 用于全过程的数据交换
    每个 stage 支持有限的重试操作，和超时，如果重试失败或超时，那么就认为任务失败。
    当任务失败时，自动处理无法进行，需要运维介入，重置 stage 或确认后人工处理
    后续改进方向：完善工作流，支持事件、stage 结果

    1. 课程开始时，创建桌面任务，任务初始化为创建阶段
        desktoptask > action: create, state: PENDING, result: , stage: BUILD, retries: 0, enabled: True
                    stage_chain: [BUILD, WAIT, ASSIGNFLOATING, DETECT]
                    context: {
                        course: 课程编号,
                        start_datetime: 桌面激活时间,
                        end_datetime: 桌面回收时间,
                        flavor: 配置类型,
                        image: 镜像,
                        network: 网络（可选）,
                        disk: 磁盘（cinder，可选),
                        ...
                    }

    2. 创建桌面处理器，发现任务，执行创建任务，创建完成后更新任务阶段，为等待 VM 状态阶段
        查找条件 retries < 3 && stage==BUILD
        进入时，state -> RUNNING
        执行： instance = novaclient.servers.create(**kwargs)
               if 失败，retries + 1，保存
                    if retires >= 3 then state=FINISHED, 发出事件，通知管理员，需要人工干预
               if 成功，stage=next_stage(), if stage is None，那么 state=FINISHED
        结束时，stage=next_stage(), if stage==END then state=FINISHED

    3. 等待阶段处理器，发现任务，如果等待未超时，那么通过 openstack 获取 vm 状态
        查找条件 stage==WAIT
        进入时 expected_states = context['expected_states'] or ['ACTIVE']
               if context['waited_at'] is not None:
                    if now - context['waited_at'] > context['wait_expires']
                    等待超时，自动处理无法介入，通知管理员并人工处理
               else context['waited_at'] = now 
        执行 instance = novaclient.servers.get(context['vm'])
             if instance.state in context['expected_states']: 
                成功，stage=next_stage(), if stage is None, 那么 state=FINISHED

    4. 分配 floating ip 阶段
        查找条件 stage==ASSIGNFLOATING
        执行 

    5. UDP、ping 检测阶段，如果此阶段还没有超时，
    
    处理的流程
    
    调度 worker 每隔 schedule_lesson_interval 秒执行
    查找 lessons 表，now + settings.lesson_ahead > lesson.start_datetime ，并且 lesson.end_datetime < now, 并且 lesson 未调度
    发出 start_lesson 任务
    更新 lesson.schedued 为 true


上课结束时 ::

    根据上课时间段关闭桌面？设置关闭延时，默认 3 分钟
    根据桌面的关闭时间关闭桌面？
    不自动关闭？

