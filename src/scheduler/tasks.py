# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# tasks
#
# 2016/2/19 fengyc : Init

from celery import Celery

app = Celery('tasks', broker='amqp://root:admin123@127.0.0.1:5672//')


@app.task
def add(x, y):
    return x + y