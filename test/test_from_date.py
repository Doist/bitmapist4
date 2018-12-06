import datetime


def test_from_date_year(bitmapist):
    ev1 = bitmapist.YearEvents.from_date('foo', datetime.datetime(2014, 1, 1))
    ev2 = bitmapist.YearEvents('foo', 2014)
    assert ev1 == ev2


def test_from_date_month(bitmapist):
    ev1 = bitmapist.MonthEvents.from_date('foo', datetime.datetime(2014, 1, 1))
    ev2 = bitmapist.MonthEvents('foo', 2014, 1)
    assert ev1 == ev2


def test_from_date_week(bitmapist):
    ev1 = bitmapist.MonthEvents.from_date('foo', datetime.datetime(2014, 1, 1))
    ev2 = bitmapist.MonthEvents('foo', 2014, 1)
    assert ev1 == ev2


def test_from_date_day(bitmapist):
    ev1 = bitmapist.DayEvents.from_date('foo', datetime.datetime(2014, 1, 1))
    ev2 = bitmapist.DayEvents('foo', 2014, 1, 1)
    assert ev1 == ev2


def test_from_date_hour(bitmapist):
    ev1 = bitmapist.HourEvents.from_date('foo', datetime.datetime(2014, 1, 1, 1))
    ev2 = bitmapist.HourEvents('foo', 2014, 1, 1, 1)
    assert ev1 == ev2
