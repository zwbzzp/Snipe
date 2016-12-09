daterange 中文设置
=======================

初始化 ::

    添加一个locale option， 在其中指定需要转换的中文，比如星期，月份即可
    
    例如
    var daterange_option = {
                "locale": {
                    "separator": " - ",
                    "applyLabel": "确定",
                    "cancelLabel": "取消",
                    "fromLabel": "从",
                    "toLabel": "到",
                    "customRangeLabel": "Custom",
                    "daysOfWeek": [
                        "日",
                        "一",
                        "二",
                        "三",
                        "四",
                        "五",
                        "六"
                    ],
                    "monthNames": [
                        "一月",
                        "二月",
                        "三月",
                        "四月",
                        "五月",
                        "六月",
                        "七月",
                        "八月",
                        "九月",
                        "十月",
                        "十一月",
                        "十二月"
                    ],
                    "firstDay": 1
                },
                opens: 'left'
    }
    
    然后把option传入daterangepicker()即可
    $('#date-range-picker').daterangepicker(daterange_option)
