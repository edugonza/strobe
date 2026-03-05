"""Tests for EventLog — internal accumulator and XES exporter."""

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from strobe.instrumentation.event_log import EventLog


async def _make_log() -> EventLog:
    log = EventLog()
    await log.add_event(
        case_id="inv-001",
        activity="tool:search",
        timestamp=datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc),
        duration_s=1.5,
        tool_args='{"query": "foo"}',
    )
    await log.add_event(
        case_id="inv-001",
        activity="llm:gemini-2.0-flash",
        timestamp=datetime(2024, 1, 1, 10, 0, 2, tzinfo=timezone.utc),
        duration_s=2.0,
        model_name="gemini-2.0-flash",
    )
    await log.add_event(
        case_id="inv-002",
        activity="tool:search",
        timestamp=datetime(2024, 1, 1, 11, 0, 0, tzinfo=timezone.utc),
        duration_s=0.8,
    )
    return log


async def test_to_dataframe_columns():
    log = await _make_log()
    df = await log.to_dataframe()
    assert EventLog.CASE_ID in df.columns
    assert EventLog.ACTIVITY in df.columns
    assert EventLog.TIMESTAMP in df.columns


async def test_to_dataframe_row_count():
    log = await _make_log()
    df = await log.to_dataframe()
    assert len(df) == 3


async def test_to_dataframe_case_ids():
    log = await _make_log()
    df = await log.to_dataframe()
    cases = set(df[EventLog.CASE_ID].unique())
    assert cases == {"inv-001", "inv-002"}


async def test_to_dataframe_strobe_namespace():
    log = await _make_log()
    df = await log.to_dataframe()
    assert "strobe:duration_s" in df.columns
    assert "strobe:tool_args" in df.columns


async def test_to_dataframe_empty():
    log = EventLog()
    df = await log.to_dataframe()
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 0


async def test_add_event_namespaces_attrs_automatically():
    log = EventLog()
    await log.add_event(
        "c1",
        "tool:x",
        datetime(2024, 1, 1, tzinfo=timezone.utc),
        duration_s=1.0,  # should become strobe:duration_s
    )
    df = await log.to_dataframe()
    assert "strobe:duration_s" in df.columns


async def test_xes_round_trip(tmp_path: Path):
    log = await _make_log()
    xes_file = tmp_path / "test.xes"
    await log.write_xes(xes_file)

    loaded = await EventLog.read_xes(xes_file)
    df_orig = await log.to_dataframe()
    df_loaded = await loaded.to_dataframe()

    assert len(df_loaded) == len(df_orig)
    assert set(df_loaded[EventLog.CASE_ID].unique()) == set(
        df_orig[EventLog.CASE_ID].unique()
    )
    assert set(df_loaded[EventLog.ACTIVITY].unique()) == set(
        df_orig[EventLog.ACTIVITY].unique()
    )
