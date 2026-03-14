"""Dash dashboard for strobe event-log analysis.

Run directly::

    python strobe/visualization/app.py

Or from Python via :func:`launch_dashboard`.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path


def launch_dashboard(xes_path: str | Path | None = None) -> subprocess.Popen:
    """Launch the Dash dashboard in a subprocess.

    Parameters
    ----------
    xes_path:
        Optional path to a ``.xes`` file. When provided, the dashboard will
        load it automatically via the ``STROBE_XES_PATH`` environment variable.

    Returns
    -------
    The :class:`subprocess.Popen` handle for the launched process.
    """
    env = os.environ.copy()
    if xes_path is not None:
        env["STROBE_XES_PATH"] = str(xes_path)

    app_file = Path(__file__).resolve()
    return subprocess.Popen(
        ["python", str(app_file)],
        env=env,
    )


# ---------------------------------------------------------------------------
# Everything below only runs when this file is executed directly.
# ---------------------------------------------------------------------------


def _run_app() -> None:  # pragma: no cover
    import base64
    import hashlib
    import tempfile
    from typing import Any, Literal, cast

    import dash
    import dash_bootstrap_components as dbc
    import pandas as pd
    import pm4py
    from dash import Input, Output, dash_table, dcc, html

    from strobe.analysis.conformance import check_conformance
    from strobe.analysis.discovery import discover_dfg, discover_process_model
    from strobe.analysis.performance import activity_statistics, throughput_times
    from strobe.visualization.plots import (
        plot_activity_statistics,
        plot_conformance,
        plot_dfg,
        plot_petri_net,
        plot_throughput_times,
    )

    _cache: dict[tuple[Any, ...], Any] = {}

    def _load_df(raw: bytes) -> pd.DataFrame:
        key = ("df", hashlib.sha256(raw).hexdigest())
        if key not in _cache:
            with tempfile.NamedTemporaryFile(suffix=".xes", delete=False) as f:
                f.write(raw)
                tmp_path = f.name
            _cache[key] = pm4py.read_xes(tmp_path)
        return _cache[key]  # type: ignore[return-value]

    def _discover(raw: bytes, algo: str, noise: float) -> tuple:
        key = ("discover", hashlib.sha256(raw).hexdigest(), algo, noise)
        if key not in _cache:
            df = _load_df(raw)
            dfg_result = discover_dfg(df)
            model_result = discover_process_model(
                df,
                algorithm=cast("Literal['inductive', 'alpha']", algo),
                noise_threshold=noise,
            )
            _cache[key] = (df, dfg_result, model_result)
        return _cache[key]  # type: ignore[return-value]

    def _conformance(raw: bytes, algo: str, noise: float) -> dict[str, float]:
        key = ("conformance", hashlib.sha256(raw).hexdigest(), algo, noise)
        if key not in _cache:
            df, _, (net, im, fm) = _discover(raw, algo, noise)
            _cache[key] = check_conformance(df, net, im, fm)
        return _cache[key]  # type: ignore[return-value]

    # ------------------------------------------------------------------
    # Pre-load from STROBE_XES_PATH env var if set
    # ------------------------------------------------------------------
    env_path = os.environ.get("STROBE_XES_PATH")
    initial_contents: str | None = None
    initial_filename: str | None = None
    if env_path:
        raw_init = Path(env_path).read_bytes()
        initial_contents = (
            "data:application/octet-stream;base64,"
            + base64.b64encode(raw_init).decode()
        )
        initial_filename = Path(env_path).name

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------
    app = dash.Dash(
        __name__,
        external_stylesheets=[dbc.themes.BOOTSTRAP],
        title="strobe dashboard",
    )

    sidebar = dbc.Col(
        [
            html.H5("Data", className="mt-3"),
            dcc.Upload(
                id="upload-xes",
                children=html.Div(["Drag & drop or ", html.A("select a XES file")]),
                style={
                    "borderWidth": "1px",
                    "borderStyle": "dashed",
                    "borderRadius": "5px",
                    "textAlign": "center",
                    "padding": "10px",
                },
                contents=initial_contents,
                filename=initial_filename,
            ),
            html.Div(id="upload-info", className="mt-2 small text-muted"),
            html.H5("Discovery", className="mt-4"),
            dcc.Dropdown(
                id="algo-select",
                options=[
                    {"label": "Inductive Miner", "value": "inductive"},
                    {"label": "Alpha Miner", "value": "alpha"},
                ],
                value="inductive",
                clearable=False,
            ),
            html.Label("Noise threshold", className="mt-3 mb-1"),
            dcc.Slider(
                id="noise-slider",
                min=0.0,
                max=1.0,
                step=0.05,
                value=0.0,
                marks={0: "0", 0.5: "0.5", 1: "1"},
            ),
        ],
        width=2,
        style={"backgroundColor": "#f8f9fa", "minHeight": "100vh", "padding": "12px"},
    )

    main_area = dbc.Col(
        [
            html.H3("strobe — Process Mining Dashboard", className="mt-3"),
            dbc.Tabs(
                [
                    dbc.Tab(label="Process model", tab_id="tab-model"),
                    dbc.Tab(label="Throughput", tab_id="tab-throughput"),
                    dbc.Tab(label="Activities", tab_id="tab-activities"),
                    dbc.Tab(label="Conformance", tab_id="tab-conformance"),
                ],
                id="main-tabs",
                active_tab="tab-model",
                className="mt-2",
            ),
            html.Div(id="tab-content", className="mt-3"),
        ],
        width=10,
    )

    app.layout = dbc.Container(
        [dbc.Row([sidebar, main_area]), dcc.Store(id="xes-store")],
        fluid=True,
    )

    # ------------------------------------------------------------------
    # Callbacks
    # ------------------------------------------------------------------

    @app.callback(
        Output("xes-store", "data"),
        Output("upload-info", "children"),
        Input("upload-xes", "contents"),
        Input("upload-xes", "filename"),
    )
    def _store_xes(
        contents: str | None, filename: str | None
    ) -> tuple[str | None, str]:
        if contents is None:
            return None, ""
        _, b64 = contents.split(",", 1)
        return b64, f"Loaded: {filename}"

    @app.callback(
        Output("noise-slider", "disabled"),
        Input("algo-select", "value"),
    )
    def _toggle_noise(algo: str) -> bool:
        return algo != "inductive"

    @app.callback(
        Output("tab-content", "children"),
        Input("main-tabs", "active_tab"),
        Input("xes-store", "data"),
        Input("algo-select", "value"),
        Input("noise-slider", "value"),
    )
    def _render_tab(active_tab: str, b64: str | None, algo: str, noise: float) -> Any:
        if b64 is None:
            return dbc.Alert("Upload a XES file in the sidebar to begin.", color="info")

        raw = base64.b64decode(b64)

        if active_tab == "tab-model":
            _, (dfg, start_acts, end_acts), (net, im, fm) = _discover(raw, algo, noise)
            return dbc.Row(
                [
                    dbc.Col(
                        [
                            html.H5("Directly-Follows Graph"),
                            dcc.Graph(figure=plot_dfg(dfg, start_acts, end_acts)),
                        ],
                        width=6,
                    ),
                    dbc.Col(
                        [
                            html.H5("Petri Net"),
                            dcc.Graph(figure=plot_petri_net(net, im, fm)),
                        ],
                        width=6,
                    ),
                ]
            )

        if active_tab == "tab-throughput":
            df, _, _ = _discover(raw, algo, noise)
            tt = throughput_times(df)
            tt_df = tt.dt.total_seconds().rename("duration_s").reset_index()
            return html.Div(
                [
                    html.H5("Per-case throughput times"),
                    dcc.Graph(figure=plot_throughput_times(tt)),
                    dash_table.DataTable(
                        data=tt_df.to_dict("records"),
                        columns=[{"name": c, "id": c} for c in tt_df.columns],
                        page_size=20,
                        style_table={"overflowX": "auto"},
                    ),
                ]
            )

        if active_tab == "tab-activities":
            df, _, _ = _discover(raw, algo, noise)
            stats = activity_statistics(df)
            stats_df = stats.reset_index()
            return html.Div(
                [
                    html.H5("Activity statistics"),
                    dcc.Graph(figure=plot_activity_statistics(stats)),
                    dash_table.DataTable(
                        data=stats_df.to_dict("records"),
                        columns=[{"name": c, "id": c} for c in stats_df.columns],
                        page_size=20,
                        style_table={"overflowX": "auto"},
                    ),
                ]
            )

        if active_tab == "tab-conformance":
            scores = _conformance(raw, algo, noise)
            return html.Div(
                [
                    html.H5("Conformance scores"),
                    dcc.Graph(figure=plot_conformance(scores)),
                    dbc.Row(
                        [
                            dbc.Col(
                                dbc.Card(
                                    dbc.CardBody(
                                        [
                                            html.H6("Fitness"),
                                            html.H4(f"{scores['fitness']:.3f}"),
                                        ]
                                    ),
                                    color="light",
                                ),
                                width=3,
                            ),
                            dbc.Col(
                                dbc.Card(
                                    dbc.CardBody(
                                        [
                                            html.H6("Precision"),
                                            html.H4(f"{scores['precision']:.3f}"),
                                        ]
                                    ),
                                    color="light",
                                ),
                                width=3,
                            ),
                            dbc.Col(
                                dbc.Card(
                                    dbc.CardBody(
                                        [
                                            html.H6("Generalization"),
                                            html.H4(f"{scores['generalization']:.3f}"),
                                        ]
                                    ),
                                    color="light",
                                ),
                                width=3,
                            ),
                            dbc.Col(
                                dbc.Card(
                                    dbc.CardBody(
                                        [
                                            html.H6("Simplicity"),
                                            html.H4(f"{scores['simplicity']:.3f}"),
                                        ]
                                    ),
                                    color="light",
                                ),
                                width=3,
                            ),
                        ],
                        className="mt-3",
                    ),
                ]
            )

        return html.Div()

    app.run(debug=False)


if __name__ == "__main__":  # pragma: no cover
    _run_app()
