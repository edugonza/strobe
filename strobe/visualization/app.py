"""Streamlit dashboard for strobe event-log analysis.

Run directly::

    streamlit run strobe/visualization/app.py

Or from Python via :func:`launch_dashboard`.
"""

from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path


def launch_dashboard(xes_path: str | Path | None = None) -> subprocess.Popen:
    """Launch the Streamlit dashboard in a subprocess.

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
        ["streamlit", "run", str(app_file)],
        env=env,
    )


# ---------------------------------------------------------------------------
# Everything below only runs when this file is executed by Streamlit.
# ---------------------------------------------------------------------------


def _run_app() -> None:  # pragma: no cover
    from typing import Literal

    import pandas as pd
    import pm4py
    import streamlit as st

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

    st.set_page_config(page_title="strobe dashboard", layout="wide")
    st.title("strobe — Process Mining Dashboard")

    # ------------------------------------------------------------------
    # Sidebar: data source + discovery options
    # ------------------------------------------------------------------
    with st.sidebar:
        st.header("Data")
        env_path = os.environ.get("STROBE_XES_PATH")
        uploaded = st.file_uploader("Upload XES file", type=["xes"])

        xes_source: bytes | None = None
        if uploaded is not None:
            xes_source = uploaded.read()
        elif env_path:
            st.info(f"Using env: {env_path}")
            xes_source = Path(env_path).read_bytes()

        st.header("Discovery")
        algorithm = st.selectbox("Algorithm", ["inductive", "alpha"])
        noise_threshold = 0.0
        if algorithm == "inductive":
            noise_threshold = st.slider(
                "Noise threshold", min_value=0.0, max_value=1.0, value=0.0, step=0.05
            )

    if xes_source is None:
        st.info("Upload a XES file in the sidebar to begin.")
        st.stop()

    # ------------------------------------------------------------------
    # Load + format event log (cached)
    # ------------------------------------------------------------------
    @st.cache_data(show_spinner="Loading event log…")
    def _load_df(raw: bytes, algo: str, noise: float) -> pd.DataFrame:
        with tempfile.NamedTemporaryFile(suffix=".xes", delete=False) as f:
            f.write(raw)
            tmp_path = f.name
        df = pm4py.read_xes(tmp_path)
        return df

    @st.cache_data(show_spinner="Discovering process model…")
    def _discover(raw: bytes, algo: Literal["inductive", "alpha"], noise: float):
        df = _load_df(raw, algo, noise)
        dfg_result = discover_dfg(df)
        model_result = discover_process_model(df, algorithm=algo, noise_threshold=noise)
        return df, dfg_result, model_result

    df, (dfg, start_acts, end_acts), (net, im, fm) = _discover(
        xes_source, algorithm, noise_threshold
    )

    # ------------------------------------------------------------------
    # Tabs
    # ------------------------------------------------------------------
    tab_model, tab_throughput, tab_activities, tab_conformance = st.tabs(
        ["Process model", "Throughput", "Activities", "Conformance"]
    )

    with tab_model:
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Directly-Follows Graph")
            st.plotly_chart(
                plot_dfg(dfg, start_acts, end_acts), use_container_width=True
            )
        with col2:
            st.subheader("Petri Net")
            st.plotly_chart(plot_petri_net(net, im, fm), use_container_width=True)

    with tab_throughput:
        st.subheader("Per-case throughput times")
        tt = throughput_times(df)
        st.plotly_chart(plot_throughput_times(tt), use_container_width=True)
        st.dataframe(
            tt.rename("duration").dt.total_seconds().rename("duration_s").reset_index()
        )

    with tab_activities:
        st.subheader("Activity statistics")
        stats = activity_statistics(df)
        st.plotly_chart(plot_activity_statistics(stats), use_container_width=True)
        st.dataframe(stats)

    with tab_conformance:
        st.subheader("Conformance scores")

        @st.cache_data(show_spinner="Running conformance check…")
        def _conformance(raw: bytes, algo: str, noise: float) -> dict[str, float]:
            df2, _, (net2, im2, fm2) = _discover(raw, algo, noise)
            return check_conformance(df2, net2, im2, fm2)

        scores = _conformance(xes_source, algorithm, noise_threshold)
        st.plotly_chart(plot_conformance(scores), use_container_width=True)

        col_fit, col_prec, col_gen, col_simp = st.columns(4)
        col_fit.metric("Fitness", f"{scores['fitness']:.3f}")
        col_prec.metric("Precision", f"{scores['precision']:.3f}")
        col_gen.metric("Generalization", f"{scores['generalization']:.3f}")
        col_simp.metric("Simplicity", f"{scores['simplicity']:.3f}")


if __name__ == "__main__" or os.environ.get(
    "STREAMLIT_SCRIPT_RUN_CTX"
):  # pragma: no cover
    _run_app()
