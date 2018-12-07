"""
Cohort is a group of subjects who share a defining characteristic (typically
subjects who experienced a common event in a selected time period, such as
birth or graduation).

You can get the cohort table using `get_cohort_table()` function. Then you may
render it yourself to HTML, or export to Pandas dataframe with df() method.

The dataframe can be further colorized (to be displayed in Jupyter notebooks)
with stylize().
"""
import datetime
try:
    import pandas as pd
except ImportError:
    pd = None


def get_cohort_table(cohort, activity, rows=20, cols=None, use_percent=True):
    # type: ("bitmapist4.events.BaseEvents", "bitmapist4.events.BaseEvents", int, int, bool) -> "CohortTable"
    """
    Return a cohort table for two provided arguments: cohort and activity.

    Each row of this table answers the question "what part of the `cohort`
    performed `activity` over time", and Nth cell of that row represents the
    number of users (absolute or in percent) which still perform the activity
    N days (or weeks, or months) after.

    Each new column of the cohort unfolds the behavior of different similar
    cohorts over time. While 0th row displays the behavior of the cohort,
    provided as an argument, 1th row displays the behavior of the similar
    cohort, but shifted 1 day (or week, or month) ago, etc.

    For example, consider following cohort statistics

    >>> table = get_cohort_table(b.WeekEvents('registered'), b.WeekEvents('active'))

    This table shows what's the rate of registered users is still active
    the same week after registration, then one week after, then two weeks
    after the registration, etc.

    The first row represents the statistics for this week's cohort (users,
    registered only this week), and naturally, will contain only one row:
    users, active this week.

    The second row represents the same statistics for users, registered last
    week. It will have two rows: the number of users, active during the
    registration week and the number of users active one week after the
    registration (that is, current week).
    """
    if cols is None:
        cols = rows
    cols = min(cols, rows)
    table = CohortTable()
    for cohort_offset in range(rows):
        cohort_to_explore = cohort.delta(-cohort_offset)  # moving backward
        base_activity = activity.delta(-cohort_offset)  # moving backward
        cohort_row = get_cohort_row(
            cohort_to_explore, base_activity, cols, use_percent=use_percent)
        table.rows.append(cohort_row)
    return table


def get_cohort_row(cohort, activity, cols, use_percent=True):
    now = datetime.datetime.utcnow()

    cohort_name = cohort.period_start().strftime('%F')
    cohort_size = len(cohort)

    row = CohortRow(cohort_name, cohort_size)
    for activity_offset in range(cols):
        current_activity = activity.delta(activity_offset)  # forward
        if current_activity.period_start() >= now:
            break
        affected_users = cohort & current_activity
        if use_percent:
            if cohort_size == 0:
                _affected = 0
            else:
                _affected = len(affected_users) * 100.0 / cohort_size
        else:
            _affected = len(affected_users)
        row.cells.append(_affected)
    return row


class CohortTable(object):
    def __init__(self, rows=None):
        self.rows = rows or []

    def __repr__(self):
        body = ',\n  '.join(repr(row) for row in self.rows)
        return 'CohortTable([\n  {}])'.format(body)

    def df(self):
        if pd is None:
            raise RuntimeError('Please pandas library')
        index = [row.name for row in self.rows]
        records = [row.cells for row in self.rows]
        sizes = [row.size for row in self.rows]
        df = pd.DataFrame.from_records(records, index=index)
        df.insert(0, 'cohort', sizes)
        return df


class CohortRow(object):
    def __init__(self, name, size, cells=None):
        self.name = name
        self.size = size
        self.cells = cells or []

    def __repr__(self):
        return 'CohortRow({0.name!r}, {0.size}, {0.cells})'.format(self)


def stylize(df, use_percent=True):
    if pd is None:
        raise RuntimeError('Please pandas library')

    if use_percent:
        string_formatter = '{:.1f}%'
        max_value = 100
    else:
        string_formatter = '{:d}'
        max_value = df.max().max()
    high_color = 250
    low_color = 100

    def _color(value):
        if pd.isnull(value):
            return 'background-color: #CCCCCC'
        normed = value * (high_color - low_color) / max_value + low_color
        return 'background-color: #64{:0X}64'.format(int(normed))

    def _fmt(value):
        if pd.isnull(value):
            return ''
        return string_formatter.format(value)

    subset = pd.IndexSlice[:, df.columns[1:]]
    return df.style.applymap(_color, subset=subset).format(_fmt, subset=subset)
