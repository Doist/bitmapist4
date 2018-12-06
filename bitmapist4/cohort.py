"""
Cohort is a group of subjects who share a defining characteristic (typically
subjects who experienced a common event in a selected time period, such as
birth or graduation).
"""
import datetime
import pandas as pd


def get_cohort_df(cohort, activity, rows=20, cols=None, use_percent=True):
    # type: ("bitmapist4.events.BaseEvents", "bitmapist4.events.BaseEvents", ...) -> pd.DataFrame
    """
    Check for the activity of a specific cohort over time

    Both cohort and activity have to be instances of BaseEvents class.
    """
    now = datetime.datetime.utcnow()

    if cols is None:
        cols = rows
    cols = min(cols, rows)

    ret_rows = []
    idx = []
    cohort_size_col = []

    for cohort_offset in range(rows):
        cohort_to_explore = cohort.delta(-cohort_offset)  # moving backward
        idx.append(cohort_to_explore.period_start().strftime('%F'))
        cohort_size_col.append(len(cohort_to_explore))

        base_activity = activity.delta(-cohort_offset)  # moving backward
        cohort_size = len(cohort_to_explore)

        activity_row = []
        for activity_offset in range(cols):
            current_activity = base_activity.delta(activity_offset)  # forward
            if current_activity.period_start() >= now:
                break
            affected_users = cohort_to_explore & current_activity
            if use_percent:
                if cohort_size == 0:
                    _affected = 0
                else:
                    _affected = len(affected_users) * 100.0 / cohort_size
            else:
                _affected = len(affected_users)
            activity_row.append(_affected)
        ret_rows.append(activity_row)

    df = pd.DataFrame.from_records(ret_rows, index=idx)
    df.insert(0, 'cohort', cohort_size_col)
    return df


def stylize(df, use_percent=True):
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

