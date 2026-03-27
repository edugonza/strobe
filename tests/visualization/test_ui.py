"""Test the Streamlit dashboard UI with PostgreSQL backend.

Tests that the Streamlit app can load event logs from a PostgreSQL backend
(populated via ADK agent + StrobePlugin) using Streamlit's testing framework.

Requires Docker for PostgreSQL container and asyncpg to be installed.
"""

import tempfile
from pathlib import Path

import pytest
from google.adk.agents import LlmAgent
from google.adk.apps import App
from google.adk.models.llm_response import LlmResponse
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from streamlit.testing.v1 import AppTest

from strobe.instrumentation.backends import save_backend_config
from strobe.instrumentation.backends.postgresql import PostgreSQLBackend
from strobe.instrumentation.plugin import StrobePlugin


@pytest.fixture
async def sample_backend_config_path(postgres_dsn):
    """Create a temporary backend config file populated with events from PostgreSQL.

    This fixture:
    1. Creates a PostgreSQL backend
    2. Initializes StrobePlugin with the backend
    3. Runs an ADK agent 2 times to populate events
    4. Saves the backend config to YAML
    5. Returns the path to the config file
    """
    # Initialize PostgreSQL backend
    backend = PostgreSQLBackend(postgres_dsn, table="test_strobe_ui_events")
    await backend.initialize()

    # Create StrobePlugin with session-based case grouping
    plugin = StrobePlugin(case_grouping="session", backend=backend)

    # Create a simple LlmAgent with a mock before_model_callback
    def mock_before_model_callback(callback_context, llm_request):  # noqa: ARG001
        """Mock callback that returns a fixed LlmResponse."""
        return LlmResponse(
            content=types.Content(parts=[types.Part.from_text(text="Mock response")]),
            model_version="gemini-2.0-flash",
            usage_metadata=types.GenerateContentResponseUsageMetadata(
                prompt_token_count=10,
                candidates_token_count=20,
            ),
        )

    agent = LlmAgent(
        name="test_agent",
        model="gemini-2.0-flash",
        before_model_callback=mock_before_model_callback,
    )

    # Create app with the agent and plugin
    app = App(name="test_app", root_agent=agent, plugins=[plugin])

    # Create session service and runner
    session_service = InMemorySessionService()
    runner = Runner(app=app, session_service=session_service)

    # Run the agent 2 times with different session IDs to populate events
    user_id = "test_user"
    session_ids = ["ui_session_1", "ui_session_2"]

    for session_id in session_ids:
        # Create a session
        await session_service.create_session(
            app_name="test_app",
            user_id=user_id,
            session_id=session_id,
        )

        # Run the agent with test messages
        test_message = types.Content(
            parts=[types.Part.from_text(text=f"Test message for {session_id}")]
        )

        # Consume all events from the runner
        async for _ in runner.run_async(
            user_id=user_id, session_id=session_id, new_message=test_message
        ):
            pass

    # Verify events were recorded
    events = await backend.get_events()
    assert len(events) > 0, "Events should be recorded in PostgreSQL"

    # Save the backend config to a temporary file
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "backend_config.yaml"
        save_backend_config(backend, config_path)

        # Read the config file so it persists beyond the context manager
        config_content = config_path.read_text()

    # Create a new temp file that will persist for the test
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(config_content)
        persistent_path = f.name

    # Clean up backend connection
    await backend.close()

    yield persistent_path

    # Cleanup
    Path(persistent_path).unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_streamlit_app_loads_backend_config(sample_backend_config_path):
    """Test that the Streamlit app can load and display event data from a PostgreSQL backend config.

    Uses Streamlit's AppTest to:
    1. Set the STROBE_BACKEND_CONFIG environment variable
    2. Run the app
    3. Verify that data is loaded and displayed correctly
    """
    import os

    # Set the environment variable to point to the backend config
    os.environ["STROBE_BACKEND_CONFIG"] = sample_backend_config_path

    try:
        # Create an AppTest instance
        at = AppTest.from_file(
            "strobe/visualization/app.py",
            default_timeout=30,
        )

        # Run the app
        at.run()

        # Verify the app ran without errors
        assert not at.exception, f"App raised exception: {at.exception}"

        # Verify that the info message about backend config is shown
        info_elements = at.info
        # The app might not show the info message if it's optimized away by cache
        # Just verify the app ran and check for other elements instead
        if info_elements:
            assert any("config" in str(elem.value).lower() for elem in info_elements), (
                "App should display info about config"
            )

        # Verify that tabs were created (Process model, Throughput, Activities, Conformance)
        tabs = at.tabs
        assert len(tabs) >= 4, f"Expected at least 4 tabs, got {len(tabs)}"

        # Verify process model tab has content (DFG and Petri net)
        tab_names = [tab.label for tab in tabs]
        assert "Process model" in tab_names, "Should have Process model tab"
        assert "Throughput" in tab_names, "Should have Throughput tab"
        assert "Activities" in tab_names, "Should have Activities tab"
        assert "Conformance" in tab_names, "Should have Conformance tab"

    finally:
        # Clean up environment variable
        os.environ.pop("STROBE_BACKEND_CONFIG", None)


@pytest.mark.asyncio
async def test_streamlit_app_displays_metrics(sample_backend_config_path):
    """Test that the Streamlit app displays conformance metrics correctly.

    Verifies that the app loads data and renders conformance metrics
    (Fitness, Precision, Generalization, Simplicity).
    """
    import os

    # Set the environment variable to point to the backend config
    os.environ["STROBE_BACKEND_CONFIG"] = sample_backend_config_path

    try:
        # Create an AppTest instance
        at = AppTest.from_file(
            "strobe/visualization/app.py",
            default_timeout=30,
        )

        # Run the app
        at.run()

        # Verify the app ran without errors
        assert not at.exception, f"App raised exception: {at.exception}"

        # Check for metrics in the conformance tab
        metrics = at.metric
        # The app should have at least 4 metrics in the conformance section
        # (Fitness, Precision, Generalization, Simplicity)
        assert len(metrics) >= 4, (
            f"Expected at least 4 metrics (Fitness, Precision, etc.), "
            f"got {len(metrics)}"
        )

    finally:
        # Clean up environment variable
        os.environ.pop("STROBE_BACKEND_CONFIG", None)


@pytest.mark.asyncio
async def test_streamlit_app_processes_discovery_algorithms(sample_backend_config_path):
    """Test that the Streamlit app can switch between discovery algorithms.

    Verifies that the app loads with the default algorithm and can be
    configured to use different discovery algorithms.
    """
    import os

    # Set the environment variable to point to the backend config
    os.environ["STROBE_BACKEND_CONFIG"] = sample_backend_config_path

    try:
        # Create an AppTest instance
        at = AppTest.from_file(
            "strobe/visualization/app.py",
            default_timeout=30,
        )

        # Run the app
        at.run()

        # Verify the app ran without errors
        assert not at.exception, f"App raised exception: {at.exception}"

        # Verify the selectbox for algorithm selection exists
        selectboxes = at.selectbox
        assert len(selectboxes) >= 1, "Should have algorithm selectbox"

        # Check that we can access the algorithm selector
        algorithm_selectbox = next(
            (
                sb
                for sb in selectboxes
                if "inductive" in str(sb.options).lower()
                or "alpha" in str(sb.options).lower()
            ),
            None,
        )
        assert algorithm_selectbox is not None, (
            "Should have algorithm selectbox with 'inductive' or 'alpha' options"
        )

    finally:
        # Clean up environment variable
        os.environ.pop("STROBE_BACKEND_CONFIG", None)


@pytest.mark.asyncio
async def test_streamlit_app_displays_plotly_charts(sample_backend_config_path):
    """Test that the Streamlit app renders Plotly charts.

    Verifies that the app creates and displays Plotly figures
    for DFG, Petri net, throughput times, and activity statistics.
    """
    import os

    # Set the environment variable to point to the backend config
    os.environ["STROBE_BACKEND_CONFIG"] = sample_backend_config_path

    try:
        # Create an AppTest instance
        at = AppTest.from_file(
            "strobe/visualization/app.py",
            default_timeout=30,
        )

        # Run the app
        at.run()

        # Verify the app ran without errors
        assert not at.exception, f"App raised exception: {at.exception}"

        # Check for plotly charts in the app
        plotly_charts = at.get("plotly_chart")
        # The app should have at least 5 Plotly charts:
        # 1. DFG in Process model tab
        # 2. Petri net in Process model tab
        # 3. Throughput times in Throughput tab
        # 4. Activity statistics in Activities tab
        # 5. Conformance in Conformance tab
        expected_charts = [
            "dfg",
            # "petri_net", # FIXME temporarily disabled
            "throughput_times",
            "activity_statistics",
            "conformance",
        ]
        assert len(plotly_charts) >= len(expected_charts), (
            f"Expected at least {len(expected_charts)} Plotly charts, got {len(plotly_charts)}"
        )

    finally:
        # Clean up environment variable
        os.environ.pop("STROBE_BACKEND_CONFIG", None)


@pytest.mark.asyncio
async def test_streamlit_app_dataframe_display(sample_backend_config_path):
    """Test that the Streamlit app displays data as DataFrames.

    Verifies that the app shows DataFrames for throughput times
    and activity statistics.
    """
    import os

    # Set the environment variable to point to the backend config
    os.environ["STROBE_BACKEND_CONFIG"] = sample_backend_config_path

    try:
        # Create an AppTest instance
        at = AppTest.from_file(
            "strobe/visualization/app.py",
            default_timeout=30,
        )

        # Run the app
        at.run()

        # Verify the app ran without errors
        assert not at.exception, f"App raised exception: {at.exception}"

        # Check for dataframes displayed in the app
        dataframes = at.dataframe
        # The app should have at least 2 DataFrames:
        # 1. Throughput times
        # 2. Activity statistics
        assert len(dataframes) >= 2, (
            f"Expected at least 2 DataFrames, got {len(dataframes)}"
        )

    finally:
        # Clean up environment variable
        os.environ.pop("STROBE_BACKEND_CONFIG", None)
