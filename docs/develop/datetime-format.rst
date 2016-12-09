日期时间格式
======================

序列化
----------------------

python 的 datetime 无法直接通过 json 序列化，需要转换为等效的字符串格式。

统一使用 iso8601 进行转换，如 ::

    import datetime
    import iso8601

    now = datetime.datetime.now()
    now_str = now.isoformat()   # 转换为 iso 格式
    now = iso8601.parse(now_str, None)  # 从字符串转换为 datetime 对象
