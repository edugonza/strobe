from __future__ import annotations

import pandas as pd

from strobe.instrumentation.event_log import EventLog


def throughput_times(df: pd.DataFrame) -> pd.Series:
    """Compute per-case wall-clock duration (last event − first event).

    Returns
    -------
    pd.Series indexed by case ID, values are :class:`~datetime.timedelta`.
    """
    ts_col = EventLog.TIMESTAMP
    case_col = EventLog.CASE_ID

    grouped = df.groupby(case_col)[ts_col]
    return grouped.max() - grouped.min()


def activity_statistics(df: pd.DataFrame) -> pd.DataFrame:
    """Compute per-activity execution statistics using ``strobe:duration_s``.

    Columns: ``count``, ``mean_duration_s``, ``min_duration_s``, ``max_duration_s``.

    If the ``strobe:duration_s`` column is absent, duration columns contain
    ``NaN``.
    """
    activity_col = EventLog.ACTIVITY
    duration_col = "strobe:duration_s"

    if duration_col not in df.columns:
        counts = df.groupby(activity_col).size().rename("count")
        stats = counts.to_frame()
        stats["mean_duration_s"] = float("nan")
        stats["min_duration_s"] = float("nan")
        stats["max_duration_s"] = float("nan")
        return stats.reset_index()

    stats = (
        df.groupby(activity_col)[duration_col]
        .agg(
            count="count",
            mean_duration_s="mean",
            min_duration_s="min",
            max_duration_s="max",
        )
        .reset_index()
    )
    stats = stats.rename(columns={activity_col: "activity"})
    return stats
