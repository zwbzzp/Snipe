系统设置——上课时段管理功能
=================================

目标使用者：管理员

使用此管理，可修改上课时段，重置上课时段

重置上课时段：未实现


核心数据模型
----------------------------------

时间表 period ::
    
    name    时间段名称

    start_time      时间段开始时间
    end_time        时间段结束时间


页面跳转逻辑
----------------------------------

只显示在一个页面中

点击编辑，对已有的上课时段进行修改；之后点击保存：修改数据库，将修改后的上课时段保存


URL 列表 ::

    /setting/setting_coursetime



核心业务逻辑
----------------------------------


已知问题、扩展
---------------------------------

