"""Tests for performance analysis functions."""
from datetime import datetime, timedelta, timezone

import pandas as pd
import pm4py
import pytest

from strobe.analysis.performance import activity_statistics, throughput_times
from strobe.instrumentation.event_log import EventLog


def _make_df() -> pd.DataFrame:
    """Two cases with fixed timestamps and known durations."""
    base = datetime(2024, 1, 1, tzinfo=timezone.utc)
    rows = [
        # case-0: spans 5 minutes
        {
            EventLog.CASE_ID: "case-0",
            EventLog.ACTIVITY: "tool:search",
            EventLog.TIMESTAMP: base,
            "strobe:duration_s": 1.0,
        },
        {
            EventLog.CASE_ID: "case-0",
            EventLog.ACTIVITY: "llm:gemini",
            EventLog.TIMESTAMP: base + timedelta(minutes=3),
            "strobe:duration_s": 2.0,
        },
        {
            EventLog.CASE_ID: "case-0",
            EventLog.ACTIVITY: "tool:search",
            EventLog.TIMESTAMP: base + timedelta(minutes=5),
            "strobe:duration_s": 0.5,
        },
        # case-1: spans 10 minutes
        {
            EventLog.CASE_ID: "case-1",
            EventLog.ACTIVITY: "tool:search",
            EventLog.TIMESTAMP: base,
            "strobe:duration_s": 3.0,
        },
        {
            EventLog.CASE_ID: "case-1",
            EventLog.ACTIVITY: "llm:gemini",
            EventLog.TIMESTAMP: base + timedelta(minutes=10),
            "strobe:duration_s": 4.0,
        },
    ]
    df = pd.DataFrame(rows)
    df = pm4py.format_dataframe(
        df,
        case_id=EventLog.CASE_ID,
        activity_key=EventLog.ACTIVITY,
        timestamp_key=EventLog.TIMESTAMP,
    )
    return df


def test_throughput_times_length():
    df = _make_df()
    result = throughput_times(df)
    assert len(result) == 2


def test_throughput_times_case0():
    df = _make_df()
    result = throughput_times(df)
    assert result["case-0"] == timedelta(minutes=5)


def test_throughput_times_case1():
    df = _make_df()
    result = throughput_times(df)
    assert result["case-1"] == timedelta(minutes=10)


def test_throughput_times_indexed_by_case():
    df = _make_df()
    result = throughput_times(df)
    assert set(result.index) == {"case-0", "case-1"}


def test_activity_statistics_columns():
    df = _make_df()
    stats = activity_statistics(df)
    assert "count" in stats.columns
    assert "mean_duration_s" in stats.columns
    assert "min_duration_s" in stats.columns
    assert "max_duration_s" in stats.columns


def test_activity_statistics_tool_search_count():
    df = _make_df()
    stats = activity_statistics(df)
    search_row = stats[stats["activity"] == "tool:search"]
    assert not search_row.empty
    assert int(search_row.iloc[0]["count"]) == 3


def test_activity_statistics_llm_mean_duration():
    df = _make_df()
    stats = activity_statistics(df)
    llm_row = stats[stats["activity"] == "llm:gemini"]
    assert not llm_row.empty
    assert llm_row.iloc[0]["mean_duration_s"] == pytest.approx(3.0)  # (2+4)/2


def test_activity_statistics_no_duration_col():
    """Should still work when strobe:duration_s is absent."""
    base = datetime(2024, 1, 1, tzinfo=timezone.utc)
    rows = [
        {EventLog.CASE_ID: "c0", EventLog.ACTIVITY: "A", EventLog.TIMESTAMP: base},
        {EventLog.CASE_ID: "c0", EventLog.ACTIVITY: "B", EventLog.TIMESTAMP: base},
    ]
    df = pd.DataFrame(rows)
    df = pm4py.format_dataframe(
        df,
        case_id=EventLog.CASE_ID,
        activity_key=EventLog.ACTIVITY,
        timestamp_key=EventLog.TIMESTAMP,
    )
    stats = activity_statistics(df)
    assert len(stats) == 2
    import math
    assert all(math.isnan(v) for v in stats["mean_duration_s"])
