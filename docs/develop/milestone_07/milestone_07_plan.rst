milestone 07 计划
==================

整理代码结构，进行业务层的重构，减少冗余代码，同时让整体结构更加合理

milestone 07 调整结构为 ::

    client -> flask views -> web （生成页面）
                          -> api (提供数据、操作，采用 rest 结构，使用 json-api 描述数据)

web 采用目前的 views 和 template 
