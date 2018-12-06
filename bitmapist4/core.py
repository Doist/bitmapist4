# -*- coding: utf-8 -*-
from contextlib import contextmanager
try:
    from typing import Type
except ImportError:  # Python 2.x
    pass

import redis
import datetime
from bitmapist4 import events as ev


class Bitmapist(object):
    """
    Core bitmapist object
    """

    # Should hourly be tracked as default?
    # Note that this can have huge implications in amounts
    # of memory that Redis uses (especially with huge integers)
    track_hourly = False

    # Should unique events be tracked as default?
    track_unique = False

    def __init__(self,
                 connection_or_url=redis.StrictRedis(),
                 track_hourly=False,
                 track_unique=True,
                 finished_ops_expire=3600 * 24,
                 unfinished_ops_expire=60,
                 key_prefix='bitmapist_'):
        if isinstance(connection_or_url, redis.StrictRedis):
            self.connection = connection_or_url
        else:
            self.connection = redis.StrictRedis.from_url(connection_or_url)
        self.track_hourly = track_hourly
        self.track_unique = track_unique
        self.finished_ops_expire = finished_ops_expire
        self.unfinished_ops_expire = unfinished_ops_expire
        self.key_prefix = key_prefix
        self.pipe = None

        kw = {'bitmapist': self}
        self.UniqueEvents = type('UniqueEvents', (ev.UniqueEvents, ),
                                 kw)  # type: Type[ev.UniqueEvents]
        self.YearEvents = type('YearEvents', (ev.YearEvents, ),
                               kw)  # type: Type[ev.YearEvents]
        self.MonthEvents = type('MonthEvents', (ev.MonthEvents, ),
                                kw)  # type: Type[ev.MonthEvents]
        self.WeekEvents = type('WeekEvents', (ev.WeekEvents, ),
                               kw)  # type: Type[ev.WeekEvents]
        self.DayEvents = type('DayEvents', (ev.DayEvents, ),
                              kw)  # type: Type[ev.DayEvents]
        self.HourEvents = type('HourEvents', (ev.HourEvents, ),
                               kw)  # type: Type[ev.HourEvents]
        self.BitOpAnd = type('BitOpAnd', (ev.BitOpAnd, ),
                             kw)  # type: Type[ev.BitOpAnd]
        self.BitOpOr = type('BitOpOr', (ev.BitOpOr, ),
                            kw)  # type: Type[ev.BitOpOr]
        self.BitOpXor = type('BitOpXor', (ev.BitOpXor, ),
                             kw)  # type: Type[ev.BitOpXor]
        self.BitOpNot = type('BitOpNot', (ev.BitOpNot, ),
                             kw)  # type: Type[ev.BitOpNot]

    def mark_event(self,
                   event_name,
                   uuid,
                   timestamp=None,
                   track_hourly=None,
                   track_unique=None):
        """
        Marks an event as "happened" for a specific moment. The function
        stores the event for the day, week and month, and optionally
        for the hour, as well as the unique event.

        - event_name is the name of the event to track
        - uuid is the unique id of the subject (typically user id). The id
          should not be huge
        - timestamp is an optional moment of time which date should be used as
          a reference point, default is to `datetime.utcnow()`

        Examples:

            # Mark id 1 as active
            b.mark_event('active', 1)

            # Mark task completed for id 252
            b.mark_event('tasks:completed', 252)
        """
        self._mark(event_name, uuid, timestamp, 1, track_hourly, track_unique)

    def unmark_event(self,
                     event_name,
                     uuid,
                     timestamp=None,
                     track_hourly=None,
                     track_unique=None):
        """
        Marks an event as "not happened" for a specific moment. The function
        stores the event for the day, week and month, and optionally
        for the hour, as well as the unique event.
        """
        self._mark(event_name, uuid, timestamp, 0, track_hourly, track_unique)

    def _mark(self, event_name, uuid, timestamp, value, track_hourly,
              track_unique):
        if timestamp is None:
            timestamp = datetime.datetime.utcnow()
        if track_hourly is None:
            track_hourly = self.track_hourly
        if track_unique is None:
            track_unique = self.track_unique

        obj_classes = [self.MonthEvents, self.WeekEvents, self.DayEvents]
        if track_hourly:
            obj_classes.append(self.HourEvents)
        if track_unique:
            obj_classes.append(self.UniqueEvents)

        if self.pipe is None:
            pipe = self.connection.pipeline()
        else:
            pipe = self.pipe

        for obj_class in obj_classes:
            pipe.setbit(
                obj_class.from_date(event_name, timestamp).redis_key, uuid,
                value)

        if self.pipe is None:
            pipe.execute()

    def start_transaction(self):
        if self.pipe is not None:
            raise RuntimeError("Transaction already started")
        self.pipe = self.connection.pipeline()

    def commit_transaction(self):
        if self.pipe is None:
            raise RuntimeError("Transaction not started")
        self.pipe.execute()
        self.pipe = None

    def rollback_transaction(self):
        self.pipe = None

    @contextmanager
    def transaction(self):
        self.start_transaction()
        try:
            yield
            self.commit_transaction()
        except:
            self.rollback_transaction()
            raise

    def mark_unique(self, event_name, uuid):
        """
        Mark unique event as "happened with a user"

        Unique event (aka "user flag") is an event which doesn't depend on date.
        Can be used for storing user properties, A/B testing, extra filtering,
        etc.

        - event_name: The name of the event, could be "active" or "new_signups"
        - uuid:  a unique id, typically user id. The id should not be huge

        Example:

            # Mark id 42 as premium
            b.mark_unique('premium', 42)
        """
        self._mark_unique(event_name, uuid, value=1)

    def unmark_unique(self, event_name, uuid):
        """
        Mark unique event as "not happened with a user"

        Unique event (aka "user flag") is an event which doesn't depend on date.
        Can be used for storing user properties, A/B testing, extra filtering,
        etc.

        - event_name: The name of the event, could be "active" or "new_signups"
        - uuid:  a unique id, typically user id. The id should not be huge

        Example:

            # Mark id 42 as premium
            b.unmark_unique('premium', 42)
        """
        self._mark_unique(event_name, uuid, value=0)

    def _mark_unique(self, event_name, uuid, value):
        conn = self.connection if self.pipe is None else self.pipe
        redis_key = self.UniqueEvents(event_name).redis_key
        conn.setbit(redis_key, uuid, value)

    def get_event_names(self, prefix='', batch=10000):
        """
        Return the list of all event names, with no particular order. Optional
        `prefix` value is used to filter only subset of keys
        """
        expr = '{}{}*'.format(self.key_prefix, prefix)
        ret = set()
        for result in self.connection.scan_iter(match=expr, count=batch):
            result = result.decode()
            chunks = result.split('_')
            event_name = '_'.join(chunks[1:-1])
            if not event_name.startswith('bitop_'):
                ret.add(event_name)
        return sorted(ret)

    def delete_all_events(self):
        """
        Delete all events from the database.
        """
        keys = self.connection.keys('{}*'.format(self.key_prefix))
        if len(keys) > 0:
            self.connection.delete(*keys)

    def delete_temporary_bitop_keys(self):
        """
        Delete all temporary keys that are used when using bit operations.
        """
        keys = self.connection.keys('{}bitop_*'.format(self.key_prefix))
        if len(keys) > 0:
            self.connection.delete(*keys)

    def prefix_key(self, event_name, date):
        return '{}{}_{}'.format(self.key_prefix, event_name, date)
