"""Integration test: ADK Agent with StrobePlugin on PostgreSQL.

Tests that the StrobePlugin correctly instruments a real ADK agent and stores
events in a PostgreSQL backend, with proper session-based case grouping.

Requires Docker for PostgreSQL container and asyncpg to be installed.
"""

import pytest
from google.adk.agents import LlmAgent
from google.adk.apps import App
from google.adk.models.llm_response import LlmResponse
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

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
