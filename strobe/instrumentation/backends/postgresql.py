"""PostgreSQL event storage backend using asyncpg."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from .base import StorageBackend

if TYPE_CHECKING:
    import asyncpg


class PostgreSQLBackend(StorageBackend):
    """Stores events in a PostgreSQL table via asyncpg."""

    def __init__(self, dsn: str, table: str = "strobe_events") -> None:
        """Initialize the backend.

        Args:
            dsn: Connection string, e.g. "postgresql://user:pass@localhost/strobe"
            table: Table name to store events (default: "strobe_events")
        """
        self._dsn = dsn
        self._table = table
        self._pool: asyncpg.Pool | None = None

    async def _ensure_pool(self):
        """Lazily create and return the connection pool."""
        if self._pool is None:
            try:
                import asyncpg
            except ImportError:
                raise ImportError(
                    "asyncpg is required for PostgreSQLBackend. "
                    "Install with: uv sync --extra postgres"
                )
            self._pool = await asyncpg.create_pool(self._dsn)
        return self._pool

    async def initialize(self) -> None:
        """Create the table and indexes."""
        pool = await self._ensure_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {self._table} (
                    id          BIGSERIAL PRIMARY KEY,
                    case_id     TEXT        NOT NULL,
                    activity    TEXT        NOT NULL,
                    timestamp   TIMESTAMPTZ NOT NULL,
                    attrs       JSONB       NOT NULL DEFAULT '{{}}'
                )
                """
            )
            await conn.execute(
                f"CREATE INDEX IF NOT EXISTS "
                f"idx_{self._table}_case_id ON {self._table}(case_id)"
            )
            await conn.execute(
                f"CREATE INDEX IF NOT EXISTS "
                f"idx_{self._table}_activity ON {self._table}(activity)"
            )
            await conn.execute(
                f"CREATE INDEX IF NOT EXISTS "
                f"idx_{self._table}_timestamp ON {self._table}(timestamp)"
            )

    async def append_event(self, event: dict) -> None:
        """Insert one event into the table."""
        pool = await self._ensure_pool()
        case_id = event.get("case:concept:name")
        activity = event.get("concept:name")
        timestamp = event.get("time:timestamp")

        # Extract strobe: attributes into JSONB column
        attrs = {k: v for k, v in event.items() if k.startswith("strobe:")}

        async with pool.acquire() as conn:
            await conn.execute(
                f"""
                INSERT INTO {self._table} (case_id, activity, timestamp, attrs)
                VALUES ($1, $2, $3, $4)
                """,
                case_id,
                activity,
                timestamp,
                json.dumps(attrs),
            )

    async def get_events(self) -> list[dict]:
        """Retrieve all events in timestamp order."""
        pool = await self._ensure_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                f"SELECT case_id, activity, timestamp, attrs FROM {self._table} "
                f"ORDER BY timestamp, id"
            )

        events = []
        for row in rows:
            event = {
                "case:concept:name": row["case_id"],
                "concept:name": row["activity"],
                "time:timestamp": row["timestamp"],
            }
            # asyncpg returns JSONB as dict, but may need parsing if it's a string
            attrs = row["attrs"]
            if isinstance(attrs, str):
                attrs = json.loads(attrs) if attrs else {}
            else:
                attrs = attrs or {}
            event.update(attrs)
            events.append(event)

        return events

    async def close(self) -> None:
        """Close the connection pool."""
        if self._pool is not None:
            await self._pool.close()
