"""Unit tests for strobe.visualization.app Dash callbacks.

Callbacks are tested as plain Python functions — no browser required.
The ``create_app()`` factory returns ``(app, callbacks)`` where *callbacks*
is a dict of the raw callback functions, making them directly callable.
"""

from __future__ import annotations

import base64
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import pm4py
import pytest

from strobe.instrumentation.event_log import EventLog
from strobe.visualization.app import create_app, launch_dashboard


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_xes_bytes() -> bytes:
    """Build a minimal XES file (3 traces, activities A/B/C) and return bytes."""
    base = datetime(2024, 1, 1, tzinfo=timezone.utc)
    rows = []
    for i, trace in enumerate([["A", "B", "C"], ["A", "B", "C"], ["A", "C"]]):
        for j, act in enumerate(trace):
            rows.append(
                {
                    EventLog.CASE_ID: f"case-{i}",
                    EventLog.ACTIVITY: act,
                    EventLog.TIMESTAMP: base + timedelta(hours=i, minutes=j),
                    "strobe:duration_s": float(j + 1),
                }
            )
    df = pd.DataFrame(rows)
    df = pm4py.format_dataframe(
        df,
        case_id=EventLog.CASE_ID,
        activity_key=EventLog.ACTIVITY,
        timestamp_key=EventLog.TIMESTAMP,
    )
    with tempfile.NamedTemporaryFile(suffix=".xes", delete=False) as f:
        tmp_path = f.name
    pm4py.write_xes(df, tmp_path)
    return Path(tmp_path).read_bytes()


@pytest.fixture(scope="module")
def xes_bytes() -> bytes:
    return _make_xes_bytes()


@pytest.fixture(scope="module")
def xes_b64(xes_bytes: bytes) -> str:
    return base64.b64encode(xes_bytes).decode()


# ---------------------------------------------------------------------------
# App creation
# ---------------------------------------------------------------------------


def test_create_app_returns_dash_instance() -> None:
    import dash

    app, _ = create_app()
    assert isinstance(app, dash.Dash)


def test_create_app_has_layout() -> None:
    app, _ = create_app()
    assert app.layout is not None


def test_create_app_exposes_all_callbacks() -> None:
    _, callbacks = create_app()
    assert set(callbacks) == {"store_xes", "toggle_noise", "render_tab"}


def test_create_app_with_xes_bytes_preloads(xes_bytes: bytes) -> None:
    """Passing xes_bytes sets initial_contents on the upload widget."""
    app, _ = create_app(xes_bytes=xes_bytes)
    # The dcc.Upload component should have contents pre-populated
    upload = app.layout.children[0].children[0].children[1]
    assert upload.contents is not None
    assert upload.contents.startswith("data:application/octet-stream;base64,")


def test_launch_dashboard_is_callable() -> None:
    assert callable(launch_dashboard)


# ---------------------------------------------------------------------------
# _store_xes callback
# ---------------------------------------------------------------------------


def test_store_xes_returns_none_for_no_upload() -> None:
    _, callbacks = create_app()
    data, info = callbacks["store_xes"](None, None)
    assert data is None
    assert info == ""


def test_store_xes_strips_data_url_prefix(xes_bytes: bytes) -> None:
    _, callbacks = create_app()
    b64 = base64.b64encode(xes_bytes).decode()
    contents = f"data:application/octet-stream;base64,{b64}"
    data, info = callbacks["store_xes"](contents, "my_log.xes")
    assert data == b64


def test_store_xes_includes_filename_in_info(xes_bytes: bytes) -> None:
    _, callbacks = create_app()
    b64 = base64.b64encode(xes_bytes).decode()
    contents = f"data:application/octet-stream;base64,{b64}"
    _, info = callbacks["store_xes"](contents, "my_log.xes")
    assert "my_log.xes" in info


# ---------------------------------------------------------------------------
# _toggle_noise callback
# ---------------------------------------------------------------------------


def test_toggle_noise_disabled_for_alpha() -> None:
    _, callbacks = create_app()
    assert callbacks["toggle_noise"]("alpha") is True


def test_toggle_noise_enabled_for_inductive() -> None:
    _, callbacks = create_app()
    assert callbacks["toggle_noise"]("inductive") is False


# ---------------------------------------------------------------------------
# _render_tab callback — no data
# ---------------------------------------------------------------------------


def test_render_tab_returns_alert_without_data() -> None:
    import dash_bootstrap_components as dbc

    _, callbacks = create_app()
    result = callbacks["render_tab"]("tab-model", None, "inductive", 0.0)
    assert isinstance(result, dbc.Alert)


# ---------------------------------------------------------------------------
# _render_tab callback — with XES data
# ---------------------------------------------------------------------------


def test_render_tab_model_returns_row(xes_b64: str) -> None:
    import dash_bootstrap_components as dbc

    _, callbacks = create_app()
    result = callbacks["render_tab"]("tab-model", xes_b64, "inductive", 0.0)
    assert isinstance(result, dbc.Row)
    assert len(result.children) == 2  # DFG column + Petri net column


def test_render_tab_model_alpha_algorithm(xes_b64: str) -> None:
    import dash_bootstrap_components as dbc

    _, callbacks = create_app()
    result = callbacks["render_tab"]("tab-model", xes_b64, "alpha", 0.0)
    assert isinstance(result, dbc.Row)


def test_render_tab_throughput_returns_div(xes_b64: str) -> None:
    from dash import html

    _, callbacks = create_app()
    result = callbacks["render_tab"]("tab-throughput", xes_b64, "inductive", 0.0)
    assert isinstance(result, html.Div)


def test_render_tab_activities_returns_div(xes_b64: str) -> None:
    from dash import html

    _, callbacks = create_app()
    result = callbacks["render_tab"]("tab-activities", xes_b64, "inductive", 0.0)
    assert isinstance(result, html.Div)


def test_render_tab_conformance_returns_div(xes_b64: str) -> None:
    from dash import html

    _, callbacks = create_app()
    result = callbacks["render_tab"]("tab-conformance", xes_b64, "inductive", 0.0)
    assert isinstance(result, html.Div)


def test_render_tab_unknown_returns_empty_div(xes_b64: str) -> None:
    from dash import html

    _, callbacks = create_app()
    result = callbacks["render_tab"]("tab-unknown", xes_b64, "inductive", 0.0)
    assert isinstance(result, html.Div)
    assert result.children is None


def test_render_tab_inductive_noise_threshold(xes_b64: str) -> None:
    import dash_bootstrap_components as dbc

    _, callbacks = create_app()
    result = callbacks["render_tab"]("tab-model", xes_b64, "inductive", 0.2)
    assert isinstance(result, dbc.Row)
