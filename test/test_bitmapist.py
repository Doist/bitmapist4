from datetime import datetime, timedelta


def test_mark_with_diff_days(bitmapist):
    bitmapist.mark_event('active', 123)

    # Month
    assert 123 in bitmapist.MonthEvents.from_date('active')
    assert 124 not in bitmapist.MonthEvents.from_date('active')

    # Week
    assert 123 in bitmapist.WeekEvents.from_date('active')
    assert 124 not in bitmapist.WeekEvents.from_date('active')

    # Day
    assert 123 in bitmapist.DayEvents.from_date('active')
    assert 124 not in bitmapist.DayEvents.from_date('active')

    # Hour
    assert 123 in bitmapist.HourEvents.from_date('active')
    assert 124 not in bitmapist.HourEvents.from_date('active')
    assert 124 not in bitmapist.HourEvents.from_date('active').prev()


def test_mark_unmark(bitmapist):
    now = datetime.utcnow()

    bitmapist.mark_event('active', 125)
    assert 125 in bitmapist.MonthEvents('active', now.year, now.month)

    bitmapist.unmark_event('active', 125)
    assert 125 not in bitmapist.MonthEvents('active', now.year, now.month)


def test_mark_counts(bitmapist):
    now = datetime.utcnow()

    assert bitmapist.MonthEvents('active', now.year,
                                 now.month).get_count() == 0

    bitmapist.mark_event('active', 123)
    bitmapist.mark_event('active', 23232)

    assert len(bitmapist.MonthEvents('active', now.year, now.month)) == 2


def test_mark_iter(bitmapist):
    now = datetime.utcnow()
    ev = bitmapist.MonthEvents('active', now.year, now.month)

    assert list(ev) == []

    bitmapist.mark_event('active', 5)
    bitmapist.mark_event('active', 55)
    bitmapist.mark_event('active', 555)
    bitmapist.mark_event('active', 5555)

    assert list(ev) == [5, 55, 555, 5555]


def test_different_dates(bitmapist):
    now = datetime.utcnow()
    yesterday = now - timedelta(days=1)

    bitmapist.mark_event('active', 123, timestamp=now)
    bitmapist.mark_event('active', 23232, timestamp=yesterday)

    assert bitmapist.DayEvents('active', now.year, now.month,
                               now.day).get_count() == 1

    assert bitmapist.DayEvents('active', yesterday.year, yesterday.month,
                               yesterday.day).get_count() == 1


def test_different_buckets(bitmapist):
    now = datetime.utcnow()

    bitmapist.mark_event('active', 123)
    bitmapist.mark_event('tasks:completed', 23232)

    assert bitmapist.MonthEvents('active', now.year,
                                 now.month).get_count() == 1
    assert bitmapist.MonthEvents('tasks:completed', now.year,
                                 now.month).get_count() == 1


def test_bit_operations(bitmapist, bitmapist_copy):
    now = datetime.utcnow()
    last_month = datetime.utcnow() - timedelta(days=30)

    # 123 has been active for two months
    bitmapist.mark_event('active', 123, timestamp=now)
    bitmapist.mark_event('active', 123, timestamp=last_month)

    # 224 has only been active last_month
    bitmapist.mark_event('active', 224, timestamp=last_month)

    # Assert basic premises
    assert bitmapist.MonthEvents('active', last_month.year,
                                 last_month.month).get_count() == 2
    assert bitmapist.MonthEvents('active', now.year,
                                 now.month).get_count() == 1

    # Try out with bit AND operation
    active_2_months = bitmapist_copy.BitOpAnd(
        bitmapist.MonthEvents('active', last_month.year, last_month.month),
        bitmapist.MonthEvents('active', now.year, now.month))
    assert active_2_months.get_count() == 1
    assert 123 in active_2_months
    assert 224 not in active_2_months
    active_2_months.delete()

    # Try out with bit OR operation
    assert bitmapist.BitOpOr(
        bitmapist.MonthEvents('active', last_month.year, last_month.month),
        bitmapist.MonthEvents('active', now.year, now.month)).get_count() == 2

    # Try out with a different system
    active_2_months = bitmapist.BitOpAnd(
        bitmapist.MonthEvents('active', last_month.year, last_month.month),
        bitmapist.MonthEvents('active', now.year, now.month),
    )
    assert active_2_months.get_count() == 1
    active_2_months.delete()

    # Try nested operations
    active_2_months = bitmapist.BitOpAnd(
        bitmapist.BitOpAnd(
            bitmapist.MonthEvents('active', last_month.year, last_month.month),
            bitmapist.MonthEvents('active', now.year, now.month)),
        bitmapist.MonthEvents('active', now.year, now.month))

    assert 123 in active_2_months
    assert 224 not in active_2_months
    active_2_months.delete()


def test_bit_operations_complex(bitmapist):
    now = datetime.utcnow()
    tom = now + timedelta(days=1)

    bitmapist.mark_event('task1', 111, timestamp=now)
    bitmapist.mark_event('task1', 111, timestamp=tom)
    bitmapist.mark_event('task2', 111, timestamp=now)
    bitmapist.mark_event('task2', 111, timestamp=tom)
    bitmapist.mark_event('task1', 222, timestamp=now)
    bitmapist.mark_event('task1', 222, timestamp=tom)
    bitmapist.mark_event('task2', 222, timestamp=now)
    bitmapist.mark_event('task2', 222, timestamp=tom)

    now_events = bitmapist.BitOpAnd(
        bitmapist.DayEvents('task1', now.year, now.month, now.day),
        bitmapist.DayEvents('task2', now.year, now.month, now.day))

    tom_events = bitmapist.BitOpAnd(
        bitmapist.DayEvents('task1', tom.year, tom.month, tom.day),
        bitmapist.DayEvents('task2', tom.year, tom.month, tom.day))

    both_events = bitmapist.BitOpAnd(now_events, tom_events)

    assert len(now_events) == len(tom_events)
    assert len(now_events) == len(both_events)


def test_bitop_key_sharing(bitmapist):
    today = datetime.utcnow()

    bitmapist.mark_event('task1', 111, timestamp=today)
    bitmapist.mark_event('task2', 111, timestamp=today)
    bitmapist.mark_event('task1', 222, timestamp=today)
    bitmapist.mark_event('task2', 222, timestamp=today)

    ev1_task1 = bitmapist.DayEvents('task1', today.year, today.month,
                                    today.day)
    ev1_task2 = bitmapist.DayEvents('task2', today.year, today.month,
                                    today.day)
    ev1_both = bitmapist.BitOpAnd(ev1_task1, ev1_task2)

    ev2_task1 = bitmapist.DayEvents('task1', today.year, today.month,
                                    today.day)
    ev2_task2 = bitmapist.DayEvents('task2', today.year, today.month,
                                    today.day)
    ev2_both = bitmapist.BitOpAnd(ev2_task1, ev2_task2)

    assert ev1_both.redis_key == ev2_both.redis_key
    assert len(ev1_both) == len(ev1_both) == 2
    ev1_both.delete()
    assert len(ev1_both) == len(ev1_both) == 0


def test_events_marked(bitmapist):
    now = datetime.utcnow()

    assert bitmapist.MonthEvents('active', now.year,
                                 now.month).get_count() == 0
    assert not bitmapist.MonthEvents('active', now.year,
                                     now.month).has_events_marked()

    bitmapist.mark_event('active', 123, timestamp=now)

    assert bitmapist.MonthEvents('active', now.year,
                                 now.month).get_count() == 1
    assert bitmapist.MonthEvents('active', now.year,
                                 now.month).has_events_marked()


def test_get_event_names(bitmapist):
    event_names = {'foo', 'bar', 'baz', 'spam', 'egg'}
    for e in event_names:
        bitmapist.mark_event(e, 1)
    bitmapist.BitOpAnd(bitmapist.DayEvents('foo'), bitmapist.DayEvents('bar'))
    assert set(bitmapist.get_event_names(batch=2)) == event_names


def test_get_event_names_prefix(bitmapist):
    event_names = {'foo', 'bar', 'baz', 'spam', 'egg'}
    for e in event_names:
        bitmapist.mark_event(e, 1)
    bitmapist.BitOpAnd(bitmapist.DayEvents('foo'), bitmapist.DayEvents('bar'))
    assert set(bitmapist.get_event_names(prefix='b',
                                         batch=2)) == {'bar', 'baz'}


def test_bit_operations_magic(bitmapist):
    bitmapist.mark_event('foo', 1)
    bitmapist.mark_event('foo', 2)
    bitmapist.mark_event('bar', 2)
    bitmapist.mark_event('bar', 3)
    foo = bitmapist.DayEvents('foo')
    bar = bitmapist.DayEvents('bar')
    assert list(foo & bar) == [2]
    assert list(foo | bar) == [1, 2, 3]
    assert list(foo ^ bar) == [1, 3]
    assert list(~foo & bar) == [3]


def test_year_events(bitmapist):
    bitmapist.mark_event('foo', 1)
    assert 1 in bitmapist.YearEvents('foo')
