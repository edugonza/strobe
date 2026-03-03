"""Tests for conformance checking wrappers."""

import pandas as pd
import pm4py

from strobe.analysis.conformance import check_conformance
from strobe.analysis.discovery import discover_process_model
from strobe.instrumentation.event_log import EventLog


def _sample_df() -> pd.DataFrame:
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


def test_check_conformance_returns_expected_keys():
    df = _sample_df()
    net, im, fm = discover_process_model(df)
    result = check_conformance(df, net, im, fm)
    assert set(result.keys()) == {
        "fitness",
        "precision",
        "generalization",
        "simplicity",
    }


def test_check_conformance_values_are_floats():
    df = _sample_df()
    net, im, fm = discover_process_model(df)
    result = check_conformance(df, net, im, fm)
    for key, val in result.items():
        assert isinstance(val, float), f"{key} should be float, got {type(val)}"


def test_check_conformance_fitness_range():
    df = _sample_df()
    net, im, fm = discover_process_model(df)
    result = check_conformance(df, net, im, fm)
    assert 0.0 <= result["fitness"] <= 1.0


def test_check_conformance_perfect_fit():
    """Model discovered from the same log should have fitness ~ 1."""
    df = _sample_df()
    net, im, fm = discover_process_model(df)
    result = check_conformance(df, net, im, fm)
    assert result["fitness"] >= 0.8
