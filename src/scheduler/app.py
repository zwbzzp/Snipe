# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# comment
#
# 2016/2/19 fengyc : Init

from tasks import add

if __name__ == '__main__':
    result = add.delay(3, 3)
    print(result.ready())
    print(result.get(timeout=1))