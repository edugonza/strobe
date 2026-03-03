"""Tests for EventLog — internal accumulator and XES exporter."""
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pytest

from strobe.instrumentation.event_log import EventLog


def _make_log() -> EventLog:
    log = EventLog()
    log.add_event(
        case_id="inv-001",
        activity="tool:search",
        timestamp=datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc),
        duration_s=1.5,
        tool_args='{"query": "foo"}',
    )
    log.add_event(
        case_id="inv-001",
        activity="llm:gemini-2.0-flash",
        timestamp=datetime(2024, 1, 1, 10, 0, 2, tzinfo=timezone.utc),
        duration_s=2.0,
        model_name="gemini-2.0-flash",
    )
    log.add_event(
        case_id="inv-002",
        activity="tool:search",
        timestamp=datetime(2024, 1, 1, 11, 0, 0, tzinfo=timezone.utc),
        duration_s=0.8,
    )
    return log


def test_to_dataframe_columns():
    log = _make_log()
    df = log.to_dataframe()
    assert EventLog.CASE_ID in df.columns
    assert EventLog.ACTIVITY in df.columns
    assert EventLog.TIMESTAMP in df.columns


def test_to_dataframe_row_count():
    log = _make_log()
    df = log.to_dataframe()
    assert len(df) == 3


def test_to_dataframe_case_ids():
    log = _make_log()
    df = log.to_dataframe()
    cases = set(df[EventLog.CASE_ID].unique())
    assert cases == {"inv-001", "inv-002"}


def test_to_dataframe_strobe_namespace():
    log = _make_log()
    df = log.to_dataframe()
    assert "strobe:duration_s" in df.columns
    assert "strobe:tool_args" in df.columns


def test_to_dataframe_empty():
    log = EventLog()
    df = log.to_dataframe()
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 0


def test_add_event_namespaces_attrs_automatically():
    log = EventLog()
    log.add_event(
        "c1",
        "tool:x",
        datetime(2024, 1, 1, tzinfo=timezone.utc),
        duration_s=1.0,  # should become strobe:duration_s
    )
    df = log.to_dataframe()
    assert "strobe:duration_s" in df.columns


def test_xes_round_trip(tmp_path: Path):
    log = _make_log()
    xes_file = tmp_path / "test.xes"
    log.write_xes(xes_file)

    loaded = EventLog.read_xes(xes_file)
    df_orig = log.to_dataframe()
    df_loaded = loaded.to_dataframe()

    assert len(df_loaded) == len(df_orig)
    assert set(df_loaded[EventLog.CASE_ID].unique()) == set(df_orig[EventLog.CASE_ID].unique())
    assert set(df_loaded[EventLog.ACTIVITY].unique()) == set(df_orig[EventLog.ACTIVITY].unique())
