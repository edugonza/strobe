"""Streamlit dashboard for strobe event-log analysis.

Run directly::

    streamlit run strobe/visualization/app.py

Or from Python via :func:`launch_dashboard`.
"""

from __future__ import annotations

import asyncio
import os
import subprocess
import tempfile
from pathlib import Path

from strobe import EventLog


def launch_dashboard(
    parquet_path: str | Path | None = None,
    backend_config_path: str | Path | None = None,
) -> subprocess.Popen:
    """Launch the Streamlit dashboard in a subprocess.

    Parameters
    ----------
    parquet_path:
        Optional path to a ``.parquet`` file. When provided, the dashboard will
        load it automatically via the ``STROBE_PARQUET_PATH`` environment variable.
    backend_config_path:
        Optional path to a backend config YAML file. When provided, the dashboard
        will load events from the backend via the ``STROBE_BACKEND_CONFIG`` env var.

    Returns
    -------
    The :class:`subprocess.Popen` handle for the launched process.
    """
    env = os.environ.copy()
    if parquet_path is not None:
        env["STROBE_PARQUET_PATH"] = str(parquet_path)
    if backend_config_path is not None:
        env["STROBE_BACKEND_CONFIG"] = str(backend_config_path)

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
    import streamlit as st

    from strobe.analysis.conformance import check_conformance
    from strobe.analysis.discovery import discover_dfg, discover_process_model
    from strobe.analysis.performance import activity_statistics, throughput_times
    from strobe.instrumentation.backends import load_backend_config
    from strobe.visualization.plots import (
        plot_activity_statistics,
        plot_conformance,
        plot_dfg,
        plot_throughput_times,
        trace_variants_html,
    )

    st.set_page_config(page_title="strobe dashboard", layout="wide")
    st.title("strobe — Process Mining Dashboard")

    # ------------------------------------------------------------------
    # Sidebar: data source + discovery options
    # ------------------------------------------------------------------
    with st.sidebar:
        st.header("Data")
        env_parquet_path = os.environ.get("STROBE_PARQUET_PATH")
        env_backend_config_path = os.environ.get("STROBE_BACKEND_CONFIG")

        # Data source selector
        data_source: Literal["parquet", "backend_config"] | None = None
        parquet_source: bytes | None = None
        backend_config_path: str | None = None

        # Parquet file uploader
        parquet_uploaded = st.file_uploader(
            "Upload Parquet file", type=["parquet"], key="parquet_uploader"
        )
        if parquet_uploaded is not None:
            parquet_source = parquet_uploaded.read()
            data_source = "parquet"
        elif env_parquet_path:
            st.info(f"Using Parquet from env: {env_parquet_path}")
            parquet_source = Path(env_parquet_path).read_bytes()
            data_source = "parquet"

        # Backend config file uploader
        config_uploaded = st.file_uploader(
            "Or upload backend config (YAML)",
            type=["yaml", "yml"],
            key="config_uploader",
        )
        if config_uploaded is not None:
            config_bytes = config_uploaded.read()
            if isinstance(config_bytes, bytes):
                with tempfile.NamedTemporaryFile(
                    mode="wb", suffix=".yaml", delete=False
                ) as f:
                    f.write(config_bytes)
                    backend_config_path = f.name
                    data_source = "backend_config"
        elif env_backend_config_path:
            st.info(f"Using backend config from env: {env_backend_config_path}")
            backend_config_path = env_backend_config_path
            data_source = "backend_config"

        st.header("Discovery")
        algorithm: Literal["inductive", "alpha"] = st.selectbox(
            "Algorithm", ["inductive", "alpha"]
        )
        noise_threshold = 0.0
        if algorithm == "inductive":
            noise_threshold = st.slider(
                "Noise threshold", min_value=0.0, max_value=1.0, value=0.0, step=0.05
            )

    if parquet_source is None and backend_config_path is None:
        st.info("Upload a Parquet file or backend config YAML in the sidebar to begin.")
        st.stop()

    # ------------------------------------------------------------------
    # Load + format event log (cached)
    # ------------------------------------------------------------------
    @st.cache_data(show_spinner="Loading event log…")
    def _load_df(
        source_type: Literal["parquet", "backend_config"],
        raw_parquet: bytes | None,
        config_path: str | None,
        algo: str,
        noise: float,
    ) -> pd.DataFrame:
        if source_type == "parquet":
            assert raw_parquet is not None, "raw_parquet must be set for parquet source"
            with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as f:
                f.write(raw_parquet)
                tmp_path = f.name
            df = EventLog().append_parquet(tmp_path)
        else:  # backend_config
            assert config_path is not None, (
                "config_path must be set for backend_config source"
            )

            async def _fetch_events():
                backend = load_backend_config(config_path)
                events = await backend.get_events()
                await backend.close()
                return events

            events = asyncio.run(_fetch_events())

            if not events:
                df = pd.DataFrame(
                    columns=[
                        "case:concept:name",
                        "concept:name",
                        "time:timestamp",
                    ]
                )
            else:
                df = pd.DataFrame(events)

        return df

    @st.cache_data(show_spinner="Discovering process model…")
    def _discover(
        source_type: Literal["parquet", "backend_config"],
        raw_parquet: bytes | None,
        config_path: str | None,
        algo: Literal["inductive", "alpha"],
        noise: float,
    ):
        df = _load_df(source_type, raw_parquet, config_path, algo, noise)
        dfg_result = discover_dfg(df)
        model_result = discover_process_model(df, algorithm=algo, noise_threshold=noise)
        return df, dfg_result, model_result

    source_type = data_source or "parquet"
    df, dfg, (net, im, fm) = _discover(
        source_type, parquet_source, backend_config_path, algorithm, noise_threshold
    )

    # ------------------------------------------------------------------
    # Tabs
    # ------------------------------------------------------------------
    (
        tab_model,
        tab_variants,
        tab_throughput,
        tab_activities,
        tab_conformance,
        tab_events,
    ) = st.tabs(
        [
            "Process model",
            "Trace variants",
            "Throughput",
            "Activities",
            "Conformance",
            "Events",
        ]
    )

    with tab_model:
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Directly-Follows Graph")
            st.plotly_chart(plot_dfg(dfg), use_container_width=True)
        with col2:
            st.subheader("Petri Net")
            # st.plotly_chart(plot_petri_net(net, im, fm), use_container_width=True)

    with tab_variants:
        st.subheader("Trace variants")
        import streamlit.components.v1 as components

        max_v = st.number_input(
            "Max variants to display", min_value=5, max_value=500, value=50, step=5
        )
        html = trace_variants_html(df, max_variants=int(max_v))
        components.html(html, height=560, scrolling=False)

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
        def _conformance(
            source_type: Literal["parquet", "backend_config"],
            raw: bytes | None,
            config_path: str | None,
            algo: Literal["inductive", "alpha"],
            noise: float,
        ) -> dict[str, float]:
            df2, _, (net2, im2, fm2) = _discover(
                source_type, raw, config_path, algo, noise
            )
            return check_conformance(df2, net2, im2, fm2)

        scores = _conformance(
            source_type, parquet_source, backend_config_path, algorithm, noise_threshold
        )
        st.plotly_chart(plot_conformance(scores), use_container_width=True)

        col_fit, col_prec, col_gen, col_simp = st.columns(4)
        col_fit.metric("Fitness", f"{scores['fitness']:.3f}")
        col_prec.metric("Precision", f"{scores['precision']:.3f}")
        col_gen.metric("Generalization", f"{scores['generalization']:.3f}")
        col_simp.metric("Simplicity", f"{scores['simplicity']:.3f}")

    with tab_events:
        st.subheader("Event log")
        st.caption(f"{len(df):,} events · {df['case:concept:name'].nunique():,} cases")

        search = st.text_input("Search (case ID or activity)", key="events_search")
        page_size = st.select_slider(
            "Rows per page", options=[25, 50, 100, 200], value=50
        )

        mask = (
            (
                df["case:concept:name"]
                .astype(str)
                .str.contains(search, case=False, na=False)
                | df["concept:name"]
                .astype(str)
                .str.contains(search, case=False, na=False)
            )
            if search
            else pd.Series(True, index=df.index)
        )
        filtered = df[mask]

        n_pages = max(1, (len(filtered) + page_size - 1) // page_size)

        if (
            "events_page" not in st.session_state
            or st.session_state.events_page >= n_pages
        ):
            st.session_state.events_page = 0

        col_prev, col_info, col_next = st.columns([1, 4, 1])
        with col_prev:
            if st.button("← Prev") and st.session_state.events_page > 0:
                st.session_state.events_page -= 1
        with col_info:
            st.caption(
                f"Page {st.session_state.events_page + 1} of {n_pages} ({len(filtered):,} matching events)"
            )
        with col_next:
            if st.button("Next →") and st.session_state.events_page < n_pages - 1:
                st.session_state.events_page += 1

        start = st.session_state.events_page * page_size
        st.dataframe(filtered.iloc[start : start + page_size], use_container_width=True)


if __name__ == "__main__" or os.environ.get(
    "STREAMLIT_SCRIPT_RUN_CTX"
):  # pragma: no cover
    _run_app()
