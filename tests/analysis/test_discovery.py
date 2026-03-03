"""Tests for process discovery wrappers."""
import pandas as pd
import pm4py
import pytest

from strobe.analysis.discovery import discover_dfg, discover_process_model
from strobe.instrumentation.event_log import EventLog


def _sample_df() -> pd.DataFrame:
    """Three traces: A→B→C, A→B→C, A→C."""
    from datetime import datetime, timezone, timedelta

    rows = []
    base = datetime(2024, 1, 1, tzinfo=timezone.utc)

    for i, trace in enumerate([["A", "B", "C"], ["A", "B", "C"], ["A", "C"]]):
        for j, act in enumerate(trace):
            rows.append(
                {
                    EventLog.CASE_ID: f"case-{i}",
                    EventLog.ACTIVITY: act,
                    EventLog.TIMESTAMP: base + timedelta(hours=i, minutes=j),
                }
            )

    df = pd.DataFrame(rows)
    df = pm4py.format_dataframe(
        df,
        case_id=EventLog.CASE_ID,
        activity_key=EventLog.ACTIVITY,
        timestamp_key=EventLog.TIMESTAMP,
    )
    return df


def test_discover_dfg_return_types():
    df = _sample_df()
    dfg, start_acts, end_acts = discover_dfg(df)
    assert isinstance(dfg, dict)
    assert isinstance(start_acts, dict)
    assert isinstance(end_acts, dict)


def test_discover_dfg_edges():
    df = _sample_df()
    dfg, _, _ = discover_dfg(df)
    # A→B should appear (from 2 traces)
    assert ("A", "B") in dfg
    # A→C should appear (from 1 trace with A→C directly)
    assert ("A", "C") in dfg


def test_discover_dfg_start_end_activities():
    df = _sample_df()
    _, start_acts, end_acts = discover_dfg(df)
    assert "A" in start_acts
    assert "C" in end_acts


def test_discover_process_model_inductive_return_types():
    df = _sample_df()
    net, im, fm = discover_process_model(df, algorithm="inductive")
    assert hasattr(net, "places")
    assert hasattr(net, "transitions")
    assert hasattr(im, "__iter__")
    assert hasattr(fm, "__iter__")


def test_discover_process_model_alpha_return_types():
    df = _sample_df()
    net, im, fm = discover_process_model(df, algorithm="alpha")
    assert hasattr(net, "places")
    assert hasattr(net, "transitions")


def test_discover_process_model_unknown_algorithm():
    df = _sample_df()
    with pytest.raises(ValueError, match="Unknown algorithm"):
        discover_process_model(df, algorithm="unknown")  # type: ignore[arg-type]
