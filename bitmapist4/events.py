from builtins import range, bytes
import calendar
import datetime


class BaseEvents(object):

    bitmapist = None
    redis_key = None

    def has_events_marked(self):
        return self.bitmapist.connection.exists(self.redis_key)

    def delete(self):
        self.bitmapist.connection.delete(self.redis_key)

    def __eq__(self, other):
        other_key = getattr(other, 'redis_key', None)
        if other_key is None:
            return NotImplemented
        return self.redis_key == other_key

    def get_uuids(self):
        val = self.bitmapist.connection.get(self.redis_key)
        if val is None:
            return

        val = bytes(val)

        for char_num, char in enumerate(val):
            # shortcut
            if char == 0:
                continue
            # find set bits, generate smth like [1, 0, ...]
            bits = [(char >> i) & 1 for i in range(7, -1, -1)]
            # list of positions with ones
            set_bits = list(pos for pos, val in enumerate(bits) if val)
            # yield everything we need
            for bit in set_bits:
                yield char_num * 8 + bit

    def __iter__(self):
        for item in self.get_uuids():
            yield item

    def __invert__(self):
        return self.bitmapist.BitOpNot(self)

    def __or__(self, other):
        return self.bitmapist.BitOpOr(self, other)

    def __and__(self, other):
        return self.bitmapist.BitOpAnd(self, other)

    def __xor__(self, other):
        return self.bitmapist.BitOpXor(self, other)

    def get_count(self):
        count = self.bitmapist.connection.bitcount(self.redis_key)
        return count

    def __len__(self):
        return self.get_count()

    def __contains__(self, uuid):
        if self.bitmapist.connection.getbit(self.redis_key, uuid):
            return True
        else:
            return False

    def delta(self, value):
        raise NotImplementedError('Must be implemented in subclass')

    def next(self):
        """ next object in a datetime line """
        return self.delta(value=1)

    def prev(self):
        """ prev object in a datetime line """
        return self.delta(value=-1)

    def period_start(self):
        raise NotImplementedError('Must be implemented in subclass')

    def period_end(self):
        raise NotImplementedError('Must be implemented in subclass')

    def event_finished(self):
        return self.period_end() < datetime.datetime.utcnow()

    def __repr__(self):
        return '{self.__class__.__name__}("{self.event_name}")'.format(
            self=self)


class UniqueEvents(BaseEvents):
    @classmethod
    def from_date(cls, event_name, dt=None):
        return cls(event_name)

    def __init__(self, event_name):
        self.event_name = event_name
        self.redis_key = self.bitmapist.prefix_key(event_name, 'u')

    def conn(self):
        return self.bitmapist.connection

    def delta(self, value):
        return self

    def event_finished(self):
        return False


class YearEvents(BaseEvents):
    """
    Events for a year.

    Example::

        YearEvents('active', 2012)
    """

    @classmethod
    def from_date(cls, event_name, dt=None):
        dt = dt or datetime.datetime.utcnow()
        return cls(event_name, dt.year)

    def __init__(self, event_name, year=None):
        now = datetime.datetime.utcnow()
        self.event_name = event_name
        self.year = not_none(year, now.year)

        months = []
        for m in range(1, 13):
            months.append(self.bitmapist.MonthEvents(event_name, self.year, m))
        or_op = self.bitmapist.BitOpOr(*months)
        self.redis_key = or_op.redis_key

    def delta(self, value):
        return self.__class__(self.event_name, self.year + value)

    def period_start(self):
        return datetime.datetime(self.year, 1, 1)

    def period_end(self):
        return datetime.datetime(self.year, 12, 31, 23, 59, 59, 999999)

    def __repr__(self):
        return ('{self.__class__.__name__}("{self.event_name}", '
                '{self.year})').format(self=self)


class MonthEvents(BaseEvents):
    """
    Events for a month.

    Example::

        MonthEvents('active', 2012, 10)
    """

    @classmethod
    def from_date(cls, event_name, dt=None):
        dt = dt or datetime.datetime.utcnow()
        return cls(event_name, dt.year, dt.month)

    def __init__(self, event_name, year=None, month=None):
        now = datetime.datetime.utcnow()
        self.event_name = event_name
        self.year = not_none(year, now.year)
        self.month = not_none(month, now.month)
        self.redis_key = self.bitmapist.prefix_key(
            event_name, '%s-%s' % (self.year, self.month))

    def delta(self, value):
        year, month = add_month(self.year, self.month, value)
        return self.__class__(self.event_name, year, month)

    def period_start(self):
        return datetime.datetime(self.year, self.month, 1)

    def period_end(self):
        _, day = calendar.monthrange(self.year, self.month)
        return datetime.datetime(self.year, self.month, day, 23, 59, 59,
                                 999999)

    def __repr__(self):
        return ('{self.__class__.__name__}("{self.event_name}", {self.year}, '
                '{self.month})').format(self=self)


class WeekEvents(BaseEvents):
    """
    Events for a week.

    Example::

        WeekEvents('active', 2012, 48)
    """

    @classmethod
    def from_date(cls, event_name, dt=None):
        dt = dt or datetime.datetime.utcnow()
        dt_year, dt_week, _ = dt.isocalendar()
        return cls(event_name, dt_year, dt_week)

    def __init__(self, event_name, year=None, week=None):
        now = datetime.datetime.utcnow()
        now_year, now_week, _ = now.isocalendar()
        self.event_name = event_name
        self.year = not_none(year, now_year)
        self.week = not_none(week, now_week)
        self.redis_key = self.bitmapist.prefix_key(
            event_name, 'W%s-%s' % (self.year, self.week))

    def delta(self, value):
        dt = iso_to_gregorian(self.year, self.week + value, 1)
        year, week, _ = dt.isocalendar()
        return self.__class__(self.event_name, year, week)

    def period_start(self):
        s = iso_to_gregorian(self.year, self.week, 1)  # mon
        return datetime.datetime(s.year, s.month, s.day)

    def period_end(self):
        e = iso_to_gregorian(self.year, self.week, 7)  # mon
        return datetime.datetime(e.year, e.month, e.day, 23, 59, 59, 999999)

    def __repr__(self):
        return ('{self.__class__.__name__}("{self.event_name}", {self.year}, '
                '{self.week})').format(self=self)


class DayEvents(BaseEvents):
    """
    Events for a day.

    Example::

        DayEvents('active', 2012, 10, 23)
    """

    @classmethod
    def from_date(cls, event_name, dt=None):
        dt = dt or datetime.datetime.utcnow()
        return cls(event_name, dt.year, dt.month, dt.day)

    def __init__(self, event_name, year=None, month=None, day=None):
        now = datetime.datetime.utcnow()
        self.event_name = event_name
        self.year = not_none(year, now.year)
        self.month = not_none(month, now.month)
        self.day = not_none(day, now.day)
        self.redis_key = self.bitmapist.prefix_key(
            event_name, '%s-%s-%s' % (self.year, self.month, self.day))

    def delta(self, value):
        dt = datetime.date(self.year, self.month,
                           self.day) + datetime.timedelta(days=value)
        return self.__class__(self.event_name, dt.year, dt.month, dt.day)

    def period_start(self):
        return datetime.datetime(self.year, self.month, self.day)

    def period_end(self):
        return datetime.datetime(self.year, self.month, self.day, 23, 59, 59,
                                 999999)

    def __repr__(self):
        return ('{self.__class__.__name__}("{self.event_name}", {self.year}, '
                '{self.month}, {self.day})').format(self=self)


class HourEvents(BaseEvents):
    """
    Events for a hour.

    Example::

        HourEvents('active', 2012, 10, 23, 13)
    """

    @classmethod
    def from_date(cls, event_name, dt=None):
        dt = dt or datetime.datetime.utcnow()
        return cls(event_name, dt.year, dt.month, dt.day, dt.hour)

    def __init__(self, event_name, year=None, month=None, day=None, hour=None):
        now = datetime.datetime.utcnow()
        self.event_name = event_name
        self.year = not_none(year, now.year)
        self.month = not_none(month, now.month)
        self.day = not_none(day, now.day)
        self.hour = not_none(hour, now.hour)
        self.redis_key = self.bitmapist.prefix_key(
            event_name,
            '%s-%s-%s-%s' % (self.year, self.month, self.day, self.hour))

    def delta(self, value):
        dt = datetime.datetime(self.year, self.month, self.day,
                               self.hour) + datetime.timedelta(hours=value)
        return self.__class__(self.event_name, dt.year, dt.month, dt.day,
                              dt.hour)

    def period_start(self):
        return datetime.datetime(self.year, self.month, self.day, self.hour)

    def period_end(self):
        return datetime.datetime(self.year, self.month, self.day, self.hour,
                                 59, 59, 999999)

    def __repr__(self):
        return ('{self.__class__.__name__}("{self.event_name}", {self.year}, '
                '{self.month}, {self.day}, {self.hour})').format(self=self)


class BitOperation(BaseEvents):
    """
    Base class for bit operations (AND, OR, XOR).

    Please note that each bit operation creates a new key prefixed with
    `bitmapist_bitop_`. These temporary keys can be deleted with
    `delete_temporary_bitop_keys`.

    You can even nest bit operations.

    Example::

        active_2_months = BitOpAnd(
            MonthEvents('active', last_month.year, last_month.month),
            MonthEvents('active', now.year, now.month)
        )

        active_2_months = BitOpAnd(
            BitOpAnd(
                MonthEvents('active', last_month.year, last_month.month),
                MonthEvents('active', now.year, now.month)
            ),
            MonthEvents('active', now.year, now.month)
        )

    """

    def __init__(self, op_name, *events):
        self.events = events
        event_redis_keys = [ev.redis_key for ev in events]
        self.redis_key = '%sbitop_%s_%s' % (self.bitmapist.key_prefix, op_name,
                                            '-'.join(event_redis_keys))
        if self.bitmapist.pipe is not None:
            pipe = self.bitmapist.pipe
        else:
            pipe = self.bitmapist.connection.pipeline()
        if self.event_finished():
            timeout = self.bitmapist.finished_ops_expire
        else:
            timeout = self.bitmapist.unfinished_ops_expire
        pipe.bitop(op_name, self.redis_key, *event_redis_keys)
        pipe.expire(self.redis_key, timeout)
        if not self.bitmapist.pipe:
            pipe.execute()

    def delta(self, value):
        events = [ev.delta(value) for ev in self.events]
        return self.__class__(*events)

    def event_finished(self):
        return all(ev.event_finished() for ev in self.events)

    def period_start(self):
        return min(ev.period_start() for ev in self.events)

    def period_end(self):
        return min(ev.period_end() for ev in self.events)

    def __repr__(self):
        ev_repr = ', '.join(repr(ev) for ev in self.events)
        return '{0.__class__.__name__}({1})'.format(self, ev_repr)


class BitOpAnd(BitOperation):
    def __init__(self, *events):
        super(BitOpAnd, self).__init__('AND', *events)


class BitOpOr(BitOperation):
    def __init__(self, *events):
        super(BitOpOr, self).__init__('OR', *events)


class BitOpXor(BitOperation):
    def __init__(self, *events):
        super(BitOpXor, self).__init__('XOR', *events)


class BitOpNot(BitOperation):
    def __init__(self, *events):
        super(BitOpNot, self).__init__('NOT', *events)


def add_month(year, month, delta):
    """
    Helper function which adds `delta` months to current `(year, month)` tuple
    and returns a new valid tuple `(year, month)`
    """
    year, month = divmod(year * 12 + month + delta, 12)
    if month == 0:
        month = 12
        year = year - 1
    return year, month


def not_none(*keys):
    """
    Helper function returning first value which is not None
    """
    for key in keys:
        if key is not None:
            return key


def iso_year_start(iso_year):
    """
    The gregorian calendar date of the first day of the given ISO year
    """
    fourth_jan = datetime.date(iso_year, 1, 4)
    delta = datetime.timedelta(fourth_jan.isoweekday() - 1)
    return fourth_jan - delta


def iso_to_gregorian(iso_year, iso_week, iso_day):
    """
    Gregorian calendar date for the given ISO year, week and day
    """
    year_start = iso_year_start(iso_year)
    return year_start + datetime.timedelta(
        days=iso_day - 1, weeks=iso_week - 1)
