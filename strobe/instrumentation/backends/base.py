"""Abstract base class for event storage backends."""

from abc import ABC, abstractmethod


class StorageBackend(ABC):
    """Abstract interface for storing and retrieving events."""

    @abstractmethod
    async def append_event(self, event: dict) -> None:
        """Append one event to the store.

        Args:
            event: Dictionary with case_id, activity, timestamp, and optional attributes.
        """

    @abstractmethod
    async def get_events(self) -> list[dict]:
        """Retrieve all events in chronological order.

        Returns:
            List of event dictionaries.
        """

    @abstractmethod
    async def close(self) -> None:
        """Close resources (connections, etc.). Safe to call multiple times."""
