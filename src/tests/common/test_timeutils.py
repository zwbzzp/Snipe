# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# comment
#
# 2016/2/19 fengyc : Init

import unittest
from phoenix.common.timeutils import ClockTime


class ClockTimeTest(unittest.TestCase):
    def test_from_string(self):
        ct = ClockTime()
        ct.from_string('12:00:59')
        self.assertEqual(ct.hour, 12)
        self.assertEqual(ct.minute, 0)
        self.assertEqual(ct.second, 59)

    def test_to_string(self):
        ct = ClockTime(23, 9, 7, separator=':')
        self.assertEquals(str(ct), '23:09:07')
        ct = ClockTime(23, 9, 7, format='%HH%SEP%MM')
        self.assertEqual(str(ct), '23:09')
        ct.format = '%HH%SEP%M'
        self.assertEqual(str(ct), '23:9')