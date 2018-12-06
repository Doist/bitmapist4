# -*- coding: utf-8 -*-
import pytest
import datetime


@pytest.mark.parametrize(
    'cls',
    ['HourEvents', 'DayEvents', 'WeekEvents', 'MonthEvents', 'YearEvents'])
def test_period_start_end(bitmapist, cls):
    Cls = getattr(bitmapist, cls)
    dt = datetime.datetime(2014, 1, 1, 8, 30)
    ev = Cls.from_date('foo', dt)
    assert ev.period_start() <= dt <= ev.period_end()
