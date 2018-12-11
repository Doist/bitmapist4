![bitmapist](https://raw.githubusercontent.com/Doist/bitmapist4/master/static/bitmapist.png "bitmapist")


[![Build Status](https://travis-ci.org/Doist/bitmapist4.svg?branch=master)](https://travis-ci.org/Doist/bitmapist4)

**NEW!** Try out our new standalone [bitmapist-server](https://github.com/Doist/bitmapist-server), which improves memory efficiency 443 times and makes your setup cheaper and more scaleable. It's fully compatable with bitmapist that runs on Redis.

# bitmapist: a powerful analytics library for Redis

This Python library makes it possible to implement real-time, highly scalable analytics that can answer following questions:

* Has user 123 been online today? This week? This month?
* Has user 123 performed action "X"?
* How many users have been active have this month? This hour?
* How many unique users have performed action "X" this week?
* How many % of users that were active last week are still active?
* How many % of users that were active last month are still active this month?
* What users performed action "X"?

This library is very easy to use and enables you to create your own reports easily.

Using Redis bitmaps you can store events for millions of users in a very little amount of memory (megabytes).
You should be careful about using huge ids as this could require larger amounts of memory. Ids should be in range [0, 2^32).

Additionally bitmapist can generate cohort graphs that can do following:
* Cohort over user retention
* How many % of users that were active last [days, weeks, months] are still active?
* How many % of users that performed action X also performed action Y (and this over time)
* And a lot of other things!

If you want to read more about bitmaps please read following:

* http://blog.getspool.com/2011/11/29/fast-easy-realtime-metrics-using-redis-bitmaps/
* http://redis.io/commands/setbit
* http://en.wikipedia.org/wiki/Bit_array
* http://www.slideshare.net/crashlytics/crashlytics-on-redis-analytics



# Installation

Can be installed very easily via:

    $ pip install bitmapist4


# Ports

* PHP port: https://github.com/jeremyFreeAgent/Bitter


# Examples

Setting things up:

```python
import bitmapist4
b = bitmapist4.Bitmapist()
```

Mark user 123 as active and has played a song:

```python
b.mark_event('active', 123)
b.mark_event('song:played', 123)
```

Answer if user 123 has been active this month:

```python
assert 123 in b.MonthEvents('active')
assert 123 in b.MonthEvents('song:played')
```


How many users have been active this week?:

```python
len(b.WeekEvents('active'))
```

Iterate over all users active this week:

```python
for uid in b.WeekEvents('active'):
    print(uid)
```


To explore any specific day, week, month or year instead of the current one, 
uou can create an event from any datetime object with a `from_date` static
method.

```python
specific_date = datetime.datetime(2018, 1, 1)
ev = b.MonthEvents('active').from_date(specific_date)
print(len(ev))
```

There are methods `prev` and `next` returning "sibling" events and
allowing you to walk through events in time without any sophisticated
iterators. A `delta` method allows you to jump forward or backward for
more than one step. Uniform API allows you to use all types of base events
(from hour to year) with the same code.

```python

current_month = b.MonthEvents('active')
prev_month = current_month.prev()
next_month = current_month.next()
year_ago = current_month.delta(-12)
```

Every event object has `period_start` and `period_end` methods to find a
time span of the event. This can be useful for caching values when the caching
of "events in future" is not desirable:

```python

ev = b.MonthEvent('active', dt)
if ev.period_end() < datetime.datetime.utcnow():
    cache.set('active_users_<...>', len(ev))
```


Tracking hourly is disabled (to save memory!) You can enable it with a
constructor argument.

```python
b = bitmapist4.Bitmapist(track_hourly=True)
```

Additionally you can supply an extra argument to `mark_event` to bypass the default value::

```python
b.mark_event('active', 123, track_hourly=False)
```


## Unique events

Sometimes data of the event makes little or no sense and you are more interested
if that specific event happened at least once in a lifetime for a user. 

There is a `UniqueEvents` model for this purpose. The model creates only one
Redis key and doesn't depend on the date.

You can combine unique events with other types of events.

A/B testing example:

```python

active = b.DailyEvents('active')
a = b.UniqueEvents('signup_form:classic')
b = b.UniqueEvents('signup_form:new')

print("Active users, signed up with classic form", len(active & a))
print("Active users, signed up with new form", len(active & b))
```

You can mark these users with `b.mark_unique` or you can automatically
populate the extra unique cohort for all marked keys

```python
b = bitmapist4.Bitmapist(track_unique=True)
b.mark_event('premium', 1)
assert 1 in b.UniqueEvents('premium')
``` 

## Perform bit operations

How many users that have been active last month are still active this month?

```python
ev = b.MonthEvents('active')
active_2months = ev & ev.prev() 
print(len(active_2months))

# Is 123 active for 2 months?
assert 123 in active_2months
```

Operators `&`, `|`, `^` and `~` supported.

This works with nested bit operations (imagine what you can do with this ;-))!


## Delete events

If you want to permanently remove marked events for any time period you can use the `delete()` method:

```python
ev = b.MonthEvents.from_date('active', last_month)
ev.delete()
```

If you want to remove all bitmapist events use:
```python
b.delete_all_events()
```

Results of bit operations are cached by default. They're cached for 60 seconds
for operations, contained non-finished periods, and for 24 hours otherwise.

You may want to reset the cache explicitly:

```python
ev = b.MonthEvents('active')
active_2months = ev & ev.prev() 
# Delete the temporary AND operation
active_2months.delete()

# delete all bit operations (slow if you have many millions of keys in Redis)
b.delete_temporary_bitop_keys()
```

## Bulk updates with transactions

If you often performs multiple updates at once, you can benefit from Redis
pipelines, wrapped as transactions inside bitmapist.

```python
with b.transaction():
    b.mark_event('active')
    b.mark_event('song:played')
```


# Migration from previous version

The API of the "bitmapist4.Bitmapist" instance is mostly compatible with the
API of previous version of bitmapist (module-level). Notable changes outlined
below.

- Removed the "system" attribute for choosing the server. You are supposed to
  use different Bitmapist class instances instead. If you used "system" to
  work with pipelines, you should switch to transactions instead.
- bitmapist.TRACK_HOURLY and bitmapist.TRACK_UNIQUE module-level constants
  moved to bitmapist4.Bitmapist attributes and can be set up with a class
  constructor.
- On a database level, new bitmapist4 uses "bitmapist_" prefix for Redis keys,
  while old bitmapist uses "trackist_" for historical reasons. If you want
  to keep using the old database, or want to use bitmapist and bitmapist4
  against the same database, you need to explicitly set the key prefix
  to "trackist_".
- If you use bitmapist-server, make sure that you use the version 1.2 or newer.
  This version adds the support for  EXPIRE command which is used to expire
  temporary bitop keys.


Replace old code which could look like this:

```python
import bitmapist
bitmapist.setup_redis('default', 'localhost', 6380)
...
bitmapist.mark_event('acive', user_id)
```

With something looking like this:

```python
from bitmapist4 import Bitmapist
bitmapist = Bitmapist('redis://localhost:6380', key_prefix='trackist_')
...
bitmapist.mark_event('acive', user_id)
```



# Bitmapist cohort

Cohort is a group of subjects who share a defining characteristic (typically
subjects who experienced a common event in a selected time period, such as
birth or graduation).

You can get the cohort table using `bitmapist4.cohort.get_cohort_table()` 
function. 

Each row of this table answers the question "what part of the `cohort`
performed `activity` over time", and Nth cell of that row represents the
number of users (absolute or in percent) which still perform the activity
N days (or weeks, or months) after.

Each new column of the cohort unfolds the behavior of different similar
cohorts over time. The latest row displays the behavior of the cohort,
provided as an argument, the one above displays the behavior of the similar
cohort, but shifted 1 day (or week, or month) ago, etc.

For example, consider following cohort statistics

```
table = get_cohort_table(b.WeekEvents('registered'), b.WeekEvents('active'))
```

This table shows what's the rate of registered users is still active
the same week after registration, then one week after, then two weeks
after the registration, etc.

By default the table displays 20 rows.

The first row represents the statistics from cohort of users, registered
20 weeks ago. The second row represents the same statistics for users,
registered 19 week ago, and so on until finally the latest row shows users
registered this week. Naturally, the last row will contain only one cell,
the number of users that were registered this week AND were active this
week as well.


Then you may render it yourself to HTML, or export to Pandas dataframe
with df() method.

Sample from user activity on http://www.gharchive.org/

```python
In [1]: from bitmapist4 import Bitmapist, cohort

In [2]: b = Bitmapist()

In [3]: cohort.get_cohort_table(b.WeekEvents('active'), b.WeekEvents('active'), rows=5, use_percent=False).df()
Out[3]:
             cohort       0        1        2        3        4
05 Nov 2018  137420  137420  25480.0  18358.0  21575.0  18430.0
12 Nov 2018  150975  150975  22195.0  25833.0  21165.0      NaN
19 Nov 2018  121417  121417  22477.0  15796.0      NaN      NaN
26 Nov 2018  152027  152027  25606.0      NaN      NaN      NaN
03 Dec 2018  130470  130470      NaN      NaN      NaN      NaN
```

The dataframe can be further colorized (to be displayed in Jupyter notebooks)
with stylize().


---

Copyright: 2012-2018 by Doist Ltd.

License: BSD
