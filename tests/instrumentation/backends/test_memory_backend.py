"""Tests for InMemoryBackend."""

from datetime import datetime, timezone

from strobe.instrumentation.backends.memory import InMemoryBackend


async def test_append_and_get_events():
    backend = InMemoryBackend()
    event1 = {
        "case:concept:name": "c1",
        "concept:name": "a1",
        "time:timestamp": datetime(2024, 1, 1, tzinfo=timezone.utc),
        "strobe:duration_s": 1.5,
    }
    event2 = {
        "case:concept:name": "c1",
        "concept:name": "a2",
        "time:timestamp": datetime(2024, 1, 1, 0, 0, 1, tzinfo=timezone.utc),
        "strobe:duration_s": 2.0,
    }

    await backend.append_event(event1)
    await backend.append_event(event2)

    events = await backend.get_events()
    assert len(events) == 2
    assert events[0] == event1
    assert events[1] == event2


async def test_get_events_empty():
    backend = InMemoryBackend()
    events = await backend.get_events()
    assert events == []


async def test_close_is_safe():
    backend = InMemoryBackend()
    await backend.close()  # Should not raise
    await backend.close()  # Multiple calls should be safe
