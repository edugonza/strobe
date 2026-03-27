"""Integration test: ADK Agent with StrobePlugin on PostgreSQL.

Tests that the StrobePlugin correctly instruments a real ADK agent and stores
events in a PostgreSQL backend, with proper session-based case grouping.

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

from strobe import discover_dfg
from strobe.instrumentation.backends import load_backend_config, save_backend_config
from strobe.instrumentation.backends.postgresql import PostgreSQLBackend
from strobe.instrumentation.event_log import EventLog
from strobe.instrumentation.plugin import StrobePlugin


@pytest.mark.asyncio
async def test_adk_agent_with_strobe_plugin_postgresql(postgres_dsn):
    """Test ADK agent instrumentation with StrobePlugin on PostgreSQL.

    Creates a PostgreSQL backend, initializes an ADK agent with StrobePlugin,
    runs it 3 times with different session IDs, and verifies that the resulting
    event log has 3 unique case IDs (one per session).
    """
    # Initialize PostgreSQL backend
    backend = PostgreSQLBackend(postgres_dsn, table="test_strobe_events")
    await backend.initialize()

    # Create StrobePlugin with session-based case grouping and PostgreSQL backend
    plugin = StrobePlugin(case_grouping="session", backend=backend)

    # Create a simple LlmAgent with a mock before_model_callback
    # This prevents actual LLM network calls during testing
    def mock_before_model_callback(callback_context, llm_request):  # noqa: ARG001
        """Mock callback that returns a fixed LlmResponse."""
        # Return a fixed response without calling the actual LLM
        return LlmResponse(
            content=types.Content(
                parts=[types.Part.from_text(text="Mock response from test")]
            ),
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

    # Run the agent 3 times with 3 different session IDs
    user_id = "test_user"
    session_ids = ["session_1", "session_2", "session_3"]

    for session_id in session_ids:
        # Create a session
        await session_service.create_session(
            app_name="test_app",
            user_id=user_id,
            session_id=session_id,
        )

        # Run the agent with a test message
        test_message = types.Content(
            parts=[types.Part.from_text(text=f"Test message for {session_id}")]
        )

        # Consume all events from the runner
        async for _ in runner.run_async(
            user_id=user_id, session_id=session_id, new_message=test_message
        ):
            pass

    # Verify the event log
    df = await plugin.to_dataframe()

    # Should have events recorded
    assert len(df) > 0, "Event log should have recorded events"

    # Should have 3 unique case IDs (one per session)
    unique_case_ids = df[EventLog.CASE_ID].unique()
    assert len(unique_case_ids) == 3, (
        f"Expected 3 unique case IDs (sessions), got {len(unique_case_ids)}: "
        f"{unique_case_ids}"
    )

    # Each case ID should correspond to a session
    case_ids_set = set(unique_case_ids)
    session_ids_set = set(session_ids)
    assert case_ids_set == session_ids_set, (
        f"Case IDs should match session IDs. "
        f"Cases: {case_ids_set}, Sessions: {session_ids_set}"
    )

    # Each session should have at least one event
    for session_id in session_ids:
        session_events = df[df[EventLog.CASE_ID] == session_id]
        assert len(session_events) >= 1, (
            f"Session {session_id} should have at least one event, "
            f"got {len(session_events)}"
        )

    # Clean up
    await backend.close()


@pytest.mark.asyncio
async def test_backend_config_save_and_load(postgres_dsn):
    """Test that backend configs can be saved and loaded, preserving all events.

    Creates a PostgreSQL backend, initializes an ADK agent with StrobePlugin,
    runs it once, saves the backend config to YAML, loads it back, and verifies
    that the recreated backend returns the same events.
    """
    # Initialize PostgreSQL backend
    backend = PostgreSQLBackend(postgres_dsn, table="test_strobe_events_config")
    await backend.initialize()

    # Create StrobePlugin with session-based case grouping and PostgreSQL backend
    plugin = StrobePlugin(case_grouping="session", backend=backend)

    # Create a simple LlmAgent with a mock before_model_callback
    def mock_before_model_callback(callback_context, llm_request):  # noqa: ARG001
        """Mock callback that returns a fixed LlmResponse."""
        return LlmResponse(
            content=types.Content(
                parts=[types.Part.from_text(text="Mock response from test")]
            ),
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

    # Run the agent once
    user_id = "test_user"
    session_id = "test_session"

    await session_service.create_session(
        app_name="test_app",
        user_id=user_id,
        session_id=session_id,
    )

    test_message = types.Content(parts=[types.Part.from_text(text="Test message")])

    # Consume all events from the runner
    async for _ in runner.run_async(
        user_id=user_id, session_id=session_id, new_message=test_message
    ):
        pass

    # Get original events
    original_events = await backend.get_events()

    # Save the backend config
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "backend.yaml"
        save_backend_config(backend, config_path)

        # Load the backend from config
        loaded_backend = load_backend_config(config_path)

        # Verify the loaded backend returns the same events
        loaded_events = await loaded_backend.get_events()
        assert len(loaded_events) == len(original_events), (
            f"Loaded backend should have same number of events. "
            f"Original: {len(original_events)}, Loaded: {len(loaded_events)}"
        )

        # Check that the events match (by comparing key fields)
        for orig, loaded in zip(original_events, loaded_events):
            assert orig["case:concept:name"] == loaded["case:concept:name"]
            assert orig["concept:name"] == loaded["concept:name"]
            assert orig["time:timestamp"] == loaded["time:timestamp"]

        await loaded_backend.close()

    # Clean up
    await backend.close()


@pytest.mark.asyncio
async def test_streamlit_app_yaml_config_workflow(postgres_dsn):
    """Test Streamlit app workflow: load YAML config, fetch events, convert to DataFrame.

    Creates a PostgreSQL backend with populated event log, saves config to YAML,
    and verifies the Streamlit app's data loading pipeline (loading backend from
    config YAML and converting events to DataFrame).
    """
    import pandas as pd

    # Initialize PostgreSQL backend
    backend = PostgreSQLBackend(postgres_dsn, table="test_strobe_app_yaml")
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

    # Run the agent with multiple messages to populate the event log
    user_id = "test_user"
    session_id = "test_session"

    await session_service.create_session(
        app_name="test_app",
        user_id=user_id,
        session_id=session_id,
    )

    for i in range(2):
        test_message = types.Content(
            parts=[types.Part.from_text(text=f"Test message {i + 1}")]
        )

        # Consume all events from the runner
        async for _ in runner.run_async(
            user_id=user_id, session_id=session_id, new_message=test_message
        ):
            pass

    # Get original DataFrame
    df_original = await plugin.to_dataframe()

    # Save the backend config to YAML
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "backend_config.yaml"
        save_backend_config(backend, config_path)

        # Simulate what the Streamlit app does:
        # 1. Load backend from config
        loaded_backend = load_backend_config(config_path)

        # 2. Get events from the backend
        events = await loaded_backend.get_events()

        # 3. Convert to DataFrame (same logic as Streamlit app)
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

        # Verify the loaded DataFrame matches the original
        assert len(df) == len(df_original), (
            f"DataFrame should have same number of rows. "
            f"Original: {len(df_original)}, Loaded: {len(df)}"
        )

        # Verify case IDs match
        original_cases = set(df_original["case:concept:name"].unique())
        loaded_cases = set(df["case:concept:name"].unique())
        assert original_cases == loaded_cases, (
            f"Case IDs should match. Original: {original_cases}, Loaded: {loaded_cases}"
        )

        # Verify activities match
        original_activities = set(df_original["concept:name"].unique())
        loaded_activities = set(df["concept:name"].unique())
        assert original_activities == loaded_activities, (
            f"Activities should match. "
            f"Original: {original_activities}, Loaded: {loaded_activities}"
        )

        # Verify we can perform process discovery on the loaded data
        dfg = discover_dfg(df)
        assert len(dfg.edges) > 0, "DFG should have transitions"
        assert len(dfg.start_nodes) > 0, "DFG should have start activities"
        assert len(dfg.end_nodes) > 0, "DFG should have end activities"

        await loaded_backend.close()

    # Clean up
    await backend.close()
