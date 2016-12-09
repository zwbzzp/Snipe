# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# comment
#
# 2016/2/27 fengyc : Init

import datetime
from base import FlaskTest
from app import db
from app.celery_sqlalchmey_scheduler_models import DatabaseSchedulerEntry, CrontabSchedule


class CeleryTest(FlaskTest):
    def setUp(self):
        super(CeleryTest, self).setUp()

    def test_course_schedule(self):
        now = datetime.datetime.now()
        dse = DatabaseSchedulerEntry()
        dse.name = 'create_tomorrow_desktops_at_midnight'
        dse.task = 'create_tomorrow_desktops_at_midnight'
        dse.enabled = True

        # after 30 seconds
        dtime = datetime.datetime.utcnow() + datetime.timedelta(seconds=30)

        crontab = CrontabSchedule()
        crontab.day_of_month = dtime.day
        crontab.hour = dtime.hour
        crontab.minute = dtime.minute
        crontab.month_of_year = dtime.month

        dse.crontab = crontab

        # save
        db.session.add(crontab)
        db.session.add(dse)
        db.session.commit()



