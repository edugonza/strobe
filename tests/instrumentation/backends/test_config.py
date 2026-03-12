"""Tests for backend config serialization."""

import tempfile
from pathlib import Path

import pytest

from strobe.instrumentation.backends import (
    InMemoryBackend,
    PostgreSQLBackend,
    backend_from_config,
    load_backend_config,
    save_backend_config,
)


class TestInMemoryBackendConfig:
    """Test InMemoryBackend config serialization."""

    def test_to_config(self) -> None:
        """Test that to_config returns the correct dict."""
        backend = InMemoryBackend()
        config = backend.to_config()
        assert config == {"backend": "memory"}

    def test_round_trip(self) -> None:
        """Test that a backend can be recreated from its config."""
        original = InMemoryBackend()
        config = original.to_config()
        recreated = backend_from_config(config)
        assert isinstance(recreated, InMemoryBackend)
        assert recreated.to_config() == config


class TestPostgreSQLBackendConfig:
    """Test PostgreSQLBackend config serialization."""

    def test_to_config_default_table(self) -> None:
        """Test to_config with default table name."""
        dsn = "postgresql://user:pass@localhost/db"
        backend = PostgreSQLBackend(dsn=dsn)
        config = backend.to_config()
        assert config == {
            "backend": "postgresql",
            "dsn": dsn,
            "table": "strobe_events",
        }

    def test_to_config_custom_table(self) -> None:
        """Test to_config with custom table name."""
        dsn = "postgresql://user:pass@localhost/db"
        table = "custom_events"
        backend = PostgreSQLBackend(dsn=dsn, table=table)
        config = backend.to_config()
        assert config == {
            "backend": "postgresql",
            "dsn": dsn,
            "table": table,
        }

    def test_round_trip_default_table(self) -> None:
        """Test that a backend can be recreated from its config (default table)."""
        dsn = "postgresql://user:pass@localhost/db"
        original = PostgreSQLBackend(dsn=dsn)
        config = original.to_config()
        recreated = backend_from_config(config)
        assert isinstance(recreated, PostgreSQLBackend)
        assert recreated.to_config() == config

    def test_round_trip_custom_table(self) -> None:
        """Test that a backend can be recreated from its config (custom table)."""
        dsn = "postgresql://user:pass@localhost/db"
        table = "custom_events"
        original = PostgreSQLBackend(dsn=dsn, table=table)
        config = original.to_config()
        recreated = backend_from_config(config)
        assert isinstance(recreated, PostgreSQLBackend)
        assert recreated.to_config() == config


class TestBackendFromConfig:
    """Test the backend_from_config factory function."""

    def test_memory_backend(self) -> None:
        """Test creating an InMemoryBackend from config."""
        config = {"backend": "memory"}
        backend = backend_from_config(config)
        assert isinstance(backend, InMemoryBackend)

    def test_postgresql_backend(self) -> None:
        """Test creating a PostgreSQLBackend from config."""
        dsn = "postgresql://user:pass@localhost/db"
        config = {"backend": "postgresql", "dsn": dsn}
        backend = backend_from_config(config)
        assert isinstance(backend, PostgreSQLBackend)
        assert backend.to_config()["dsn"] == dsn
        assert backend.to_config()["table"] == "strobe_events"

    def test_postgresql_backend_custom_table(self) -> None:
        """Test creating a PostgreSQLBackend with custom table from config."""
        dsn = "postgresql://user:pass@localhost/db"
        table = "custom_table"
        config = {"backend": "postgresql", "dsn": dsn, "table": table}
        backend = backend_from_config(config)
        assert isinstance(backend, PostgreSQLBackend)
        assert backend.to_config()["table"] == table

    def test_unknown_backend(self) -> None:
        """Test that unknown backend types raise ValueError."""
        config = {"backend": "unknown"}
        with pytest.raises(ValueError, match="Unknown backend type"):
            backend_from_config(config)

    def test_postgresql_missing_dsn(self) -> None:
        """Test that PostgreSQL config without DSN raises ValueError."""
        config = {"backend": "postgresql"}
        with pytest.raises(ValueError, match="requires 'dsn'"):
            backend_from_config(config)


class TestSaveAndLoadBackendConfig:
    """Test YAML save/load functions."""

    def test_save_and_load_memory(self) -> None:
        """Test saving and loading a memory backend config."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "backend.yaml"
            original = InMemoryBackend()
            save_backend_config(original, config_path)

            recreated = load_backend_config(config_path)
            assert isinstance(recreated, InMemoryBackend)
            assert recreated.to_config() == original.to_config()

    def test_save_and_load_postgresql(self) -> None:
        """Test saving and loading a PostgreSQL backend config."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "backend.yaml"
            dsn = "postgresql://user:pass@localhost/db"
            table = "my_events"
            original = PostgreSQLBackend(dsn=dsn, table=table)
            save_backend_config(original, config_path)

            recreated = load_backend_config(config_path)
            assert isinstance(recreated, PostgreSQLBackend)
            assert recreated.to_config() == original.to_config()

    def test_yaml_format(self) -> None:
        """Test that the saved YAML is properly formatted."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "backend.yaml"
            dsn = "postgresql://user:pass@localhost/db"
            backend = PostgreSQLBackend(dsn=dsn, table="events_table")
            save_backend_config(backend, config_path)

            yaml_content = config_path.read_text()
            assert "backend: postgresql" in yaml_content
            assert f"dsn: {dsn}" in yaml_content
            assert "table: events_table" in yaml_content
