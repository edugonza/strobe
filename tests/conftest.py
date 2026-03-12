"""Fixtures for integration tests."""

import pytest
from testcontainers.postgres import PostgresContainer


@pytest.fixture(scope="module")
def postgres_container():
    """Start a PostgreSQL container for the test module.

    Requires Docker to be running.
    """
    container = PostgresContainer("postgres:17", driver=None)
    container.start()
    yield container
    container.stop()


@pytest.fixture
def postgres_dsn(postgres_container):
    """Get PostgreSQL DSN from the test container.

    Returns the connection string for asyncpg.
    """
    return postgres_container.get_connection_url()
