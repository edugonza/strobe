"""Tests for PostgreSQLBackend.

These tests are skipped if asyncpg is not installed or if a PostgreSQL database
is not available.
"""

import os
from datetime import datetime, timezone

import pytest

# Skip all tests in this module if asyncpg is not installed
asyncpg = pytest.importorskip("asyncpg")

from strobe.instrumentation.backends.postgresql import PostgreSQLBackend  # noqa: E402


@pytest.fixture
async def pg_dsn():
    """Get PostgreSQL DSN from environment or use a default."""
    return os.getenv("TEST_POSTGRES_DSN", "postgresql://localhost/strobe_test")


@pytest.fixture
async def backend(pg_dsn):
    """Create a backend and initialize the database."""
    backend = PostgreSQLBackend(pg_dsn, table="test_events")
    try:
        await backend.initialize()
    except Exception as e:
        pytest.skip(f"PostgreSQL not available: {e}")
    yield backend
    await backend.close()


async def test_append_and_get_events(backend):
    """Test appending and retrieving events."""
    event1 = {
        "case:concept:name": "c1",
        "concept:name": "a1",
        "time:timestamp": datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc),
        "strobe:duration_s": 1.5,
        "strobe:tool_args": '{"query": "foo"}',
    }
    event2 = {
        "case:concept:name": "c1",
        "concept:name": "a2",
        "time:timestamp": datetime(2024, 1, 1, 10, 0, 1, tzinfo=timezone.utc),
        "strobe:duration_s": 2.0,
    }

    await backend.append_event(event1)
    await backend.append_event(event2)

    events = await backend.get_events()
    assert len(events) == 2

    # Check first event
    assert events[0]["case:concept:name"] == "c1"
    assert events[0]["concept:name"] == "a1"
    assert events[0]["strobe:duration_s"] == 1.5
    assert events[0]["strobe:tool_args"] == '{"query": "foo"}'

    # Check second event
    assert events[1]["case:concept:name"] == "c1"
    assert events[1]["concept:name"] == "a2"
    assert events[1]["strobe:duration_s"] == 2.0


async def test_get_events_ordering(backend):
    """Test that events are returned in timestamp order."""
    # Insert events in non-chronological order
    event2 = {
        "case:concept:name": "c1",
        "concept:name": "a2",
        "time:timestamp": datetime(2024, 1, 1, 10, 0, 2, tzinfo=timezone.utc),
        "strobe:duration_s": 2.0,
    }
    event1 = {
        "case:concept:name": "c1",
        "concept:name": "a1",
        "time:timestamp": datetime(2024, 1, 1, 10, 0, 1, tzinfo=timezone.utc),
        "strobe:duration_s": 1.0,
    }

    await backend.append_event(event2)
    await backend.append_event(event1)

    events = await backend.get_events()
    assert len(events) == 2
    # Should be ordered by timestamp
    assert events[0]["time:timestamp"] < events[1]["time:timestamp"]


async def test_get_events_empty(backend):
    """Test retrieving from an empty table."""
    events = await backend.get_events()
    assert events == []


async def test_close_is_safe(backend):
    """Test that close can be called multiple times."""
    await backend.close()
    await backend.close()  # Should not raise
