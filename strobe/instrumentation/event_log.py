from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd
import pm4py


class EventLog:
    """Internal accumulator that stores events and exports to XES / DataFrame."""

    CASE_ID = "case:concept:name"
    ACTIVITY = "concept:name"
    TIMESTAMP = "time:timestamp"

    def __init__(self) -> None:
        self._events: list[dict] = []

    def add_event(
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
        self._events.append(event)

    def to_dataframe(self) -> pd.DataFrame:
        """Return a pm4py-compatible DataFrame."""
        if not self._events:
            df = pd.DataFrame(columns=[self.CASE_ID, self.ACTIVITY, self.TIMESTAMP])
        else:
            df = pd.DataFrame(self._events)
        df = pm4py.format_dataframe(
            df,
            case_id=self.CASE_ID,
            activity_key=self.ACTIVITY,
            timestamp_key=self.TIMESTAMP,
        )
        return df

    def write_xes(self, path: str | Path) -> None:
        """Export the log to an XES file at *path*."""
        pm4py.write_xes(self.to_dataframe(), str(path))

    @classmethod
    def read_xes(cls, path: str | Path) -> "EventLog":
        """Load an XES file and return a new :class:`EventLog`."""
        df = pm4py.read_xes(str(path))
        log = cls()
        for _, row in df.iterrows():
            case_id = row[cls.CASE_ID]
            activity = row[cls.ACTIVITY]
            timestamp = row[cls.TIMESTAMP]
            extra = {
                k: v
                for k, v in row.items()
                if k not in (cls.CASE_ID, cls.ACTIVITY, cls.TIMESTAMP)
                and not k.startswith("@@")
            }
            log.add_event(case_id, activity, timestamp, **extra)
        return log
