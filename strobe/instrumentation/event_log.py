from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd

from .backends.base import StorageBackend
from .backends.memory import InMemoryBackend


class EventLog:
    """Internal accumulator that stores events and exports to XES / DataFrame."""

    CASE_ID = "case:concept:name"
    ACTIVITY = "concept:name"
    TIMESTAMP = "time:timestamp"

    def __init__(self, backend: StorageBackend | None = None) -> None:
        self._backend = backend or InMemoryBackend()

    async def add_event(
        self,
        case_id: str,
        activity: str,
        timestamp: datetime,
        **attrs,
    ) -> None:
        """Append one event to the log.

        Extra keyword arguments are stored under a ``strobe:`` namespace prefix
        so they survive XES round-trips.
        """
        event: dict = {
            self.CASE_ID: case_id,
            self.ACTIVITY: activity,
            self.TIMESTAMP: timestamp,
        }
        for key, value in attrs.items():
            namespaced = key if key.startswith("strobe:") else f"strobe:{key}"
            event[namespaced] = value
        await self._backend.append_event(event)

    async def to_dataframe(self) -> pd.DataFrame:
        """Return a DataFrame."""
        events = await self._backend.get_events()
        if not events:
            df = pd.DataFrame(columns=[self.CASE_ID, self.ACTIVITY, self.TIMESTAMP])
        else:
            df = pd.DataFrame(events)
        return df

    async def to_parquet(self, path: str | Path) -> None:
        """Export the log to a parquet file at *path*."""
        df = await self.to_dataframe()
        df.to_parquet(path)

    async def append_parquet(self, path: str | Path) -> EventLog:
        """Load the log from a parquet file at *path*."""
        df = pd.read_parquet(path)
        for _, row in df.iterrows():
            await self.add_event(
                case_id=row[self.CASE_ID],
                activity=row[self.ACTIVITY],
                timestamp=row[self.TIMESTAMP],
                **row.drop([self.CASE_ID, self.ACTIVITY, self.TIMESTAMP]),
            )
        return self

    async def close(self) -> None:
        """Close any backend resources."""
        await self._backend.close()
