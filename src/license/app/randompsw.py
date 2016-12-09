# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# comment
#
# 16-7-14 qinjinghui : Init

import random


def get_random_password():
      a='''0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'''
      password=''
      for i in range(7):
          password=password+random.choice(a)
      return password