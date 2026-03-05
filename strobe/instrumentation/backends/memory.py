"""In-memory event storage backend."""

from .base import StorageBackend


class InMemoryBackend(StorageBackend):
    """Stores events in a simple in-memory list."""

    def __init__(self) -> None:
        self._events: list[dict] = []

    async def append_event(self, event: dict) -> None:
        """Append one event to the in-memory list."""
        self._events.append(event)

    async def get_events(self) -> list[dict]:
        """Return all events."""
        return list(self._events)

    async def close(self) -> None:
        """No-op for in-memory backend."""
