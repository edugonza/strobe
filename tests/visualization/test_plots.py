"""Unit tests for strobe.visualization.plots figure factories."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pandas as pd
import plotly.graph_objects as go
import pytest

from strobe.analysis.traces import group_by_trace_variant
from strobe.analysis.discovery import discover_dfg, discover_process_model
from strobe.analysis.performance import activity_statistics, throughput_times
from strobe.instrumentation.event_log import EventLog
from strobe.visualization.plots import (
    plot_activity_statistics,
    plot_conformance,
    plot_dfg,
    plot_petri_net,
    plot_throughput_times,
    trace_variants_html,
)


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


def _sample_df() -> pd.DataFrame:
    """Three traces: A→B→C, A→B→C, A→C."""
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
    return df


def _perf_df() -> pd.DataFrame:
    """Two cases with strobe:duration_s for activity_statistics testing."""
    base = datetime(2024, 1, 1, tzinfo=timezone.utc)
    rows = [
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
    return df


# ---------------------------------------------------------------------------
# DFG
# ---------------------------------------------------------------------------


def test_plot_dfg_returns_figure():
    df = _sample_df()
    dfg = discover_dfg(df)
    fig = plot_dfg(dfg)
    assert isinstance(fig, go.Figure)
    assert len(fig.data) > 0


def test_plot_dfg_edge_labels_in_hover():
    df = _sample_df()
    dfg = discover_dfg(df)
    fig = plot_dfg(dfg)
    # Edge traces carry hover text with "A → B" style strings
    hover_texts = []
    for trace in fig.data:
        if trace.text:
            hover_texts.append(
                trace.text if isinstance(trace.text, str) else " ".join(trace.text)
            )
    combined = " ".join(hover_texts)
    # At least one activity name should appear
    assert "A" in combined or "B" in combined or "C" in combined


# ---------------------------------------------------------------------------
# Petri net
# ---------------------------------------------------------------------------


@pytest.mark.xfail(reason="Not implemented yet")
def test_plot_petri_net_returns_figure():
    df = _sample_df()
    net, im, fm = discover_process_model(df)
    fig = plot_petri_net(net, im, fm)
    assert isinstance(fig, go.Figure)
    assert len(fig.data) > 0


# ---------------------------------------------------------------------------
# Throughput times
# ---------------------------------------------------------------------------


def test_plot_throughput_times_returns_figure():
    df = _perf_df()
    tt = throughput_times(df)
    fig = plot_throughput_times(tt)
    assert isinstance(fig, go.Figure)


# ---------------------------------------------------------------------------
# Activity statistics
# ---------------------------------------------------------------------------


def test_plot_activity_statistics_returns_figure():
    df = _perf_df()
    stats = activity_statistics(df)
    fig = plot_activity_statistics(stats)
    assert isinstance(fig, go.Figure)


# ---------------------------------------------------------------------------
# Conformance
# ---------------------------------------------------------------------------


def test_plot_conformance_returns_figure():
    scores = {
        "fitness": 0.9,
        "precision": 0.8,
        "generalization": 0.7,
        "simplicity": 0.6,
    }
    fig = plot_conformance(scores)
    assert isinstance(fig, go.Figure)


def test_plot_conformance_all_metrics_present():
    scores = {
        "fitness": 0.9,
        "precision": 0.8,
        "generalization": 0.7,
        "simplicity": 0.6,
    }
    fig = plot_conformance(scores)
    # The bar chart y-axis contains the metric names
    bar_trace = next(t for t in fig.data if isinstance(t, go.Bar))
    y_labels = list(bar_trace.y)
    for metric in ("fitness", "precision", "generalization", "simplicity"):
        assert metric in y_labels, (
            f"{metric!r} not found in figure y-labels: {y_labels}"
        )


# ---------------------------------------------------------------------------
# Trace variants HTML
# ---------------------------------------------------------------------------


def test_trace_variants_html_returns_string():
    df = _sample_df()
    html = trace_variants_html(group_by_trace_variant(df))
    assert isinstance(html, str)
    assert "<div" in html


def test_trace_variants_html_contains_activities():
    df = _sample_df()
    html = trace_variants_html(group_by_trace_variant(df))
    assert "A" in html
    assert "B" in html
    assert "C" in html


def test_trace_variants_html_sorted_by_frequency():
    df = _sample_df()
    html = trace_variants_html(group_by_trace_variant(df))
    # A→B→C appears 2×, A→C appears 1×; "2×" must come before "1×"
    pos_2 = html.index("2\u00d7")
    pos_1 = html.index("1\u00d7")
    assert pos_2 < pos_1


def test_trace_variants_html_max_variants():
    df = _sample_df()
    html = trace_variants_html(group_by_trace_variant(df), max_variants=1)
    # Only the most frequent variant (A→B→C, 2×) shown; "1×" should not appear
    assert "2\u00d7" in html
    assert "1\u00d7" not in html


def test_trace_variants_html_empty_df():
    df = pd.DataFrame(columns=["case:concept:name", "concept:name", "time:timestamp"])
    html = trace_variants_html(group_by_trace_variant(df))
    assert isinstance(html, str)
    assert "0 variants" in html


# ---------------------------------------------------------------------------
# app.py importability
# ---------------------------------------------------------------------------


def test_app_is_importable():
    """app.py must be importable without starting a Streamlit server."""
    import importlib

    mod = importlib.import_module("strobe.visualization.app")
    assert callable(mod.launch_dashboard)
