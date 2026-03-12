"""Factory and YAML I/O utilities for storage backends."""

from __future__ import annotations

from pathlib import Path

try:
    import yaml  # type: ignore[import-untyped]
except ImportError:
    raise ImportError(
        "pyyaml is required for backend config serialization. "
        "Install with: pip install pyyaml"
    )

from .base import StorageBackend


def backend_from_config(config: dict) -> StorageBackend:
    """Create a StorageBackend instance from a config dict.

    Parameters
    ----------
    config:
        Dictionary with a 'backend' key specifying the backend type.
        For 'memory': no additional keys needed.
        For 'postgresql': requires 'dsn' key; 'table' key is optional (defaults to 'strobe_events').

    Returns
    -------
    A StorageBackend instance.

    Raises
    ------
    ValueError
        If the backend type is unknown.
    """
    kind = config.get("backend")
    if kind == "memory":
        from .memory import InMemoryBackend

        return InMemoryBackend()
    elif kind == "postgresql":
        from .postgresql import PostgreSQLBackend

        dsn = config.get("dsn")
        if dsn is None:
            raise ValueError("PostgreSQL backend requires 'dsn' in config")
        table = config.get("table", "strobe_events")
        return PostgreSQLBackend(dsn=dsn, table=table)
    else:
        raise ValueError(f"Unknown backend type: {kind!r}")


def save_backend_config(backend: StorageBackend, path: str | Path) -> None:
    """Save a backend's config to a YAML file.

    Parameters
    ----------
    backend:
        The StorageBackend instance to serialize.
    path:
        File path where the YAML config will be written.
    """
    config = backend.to_config()
    Path(path).write_text(yaml.safe_dump(config))


def load_backend_config(path: str | Path) -> StorageBackend:
    """Load a backend from a YAML config file.

    Parameters
    ----------
    path:
        File path to the YAML config.

    Returns
    -------
    A StorageBackend instance recreated from the config.
    """
    config = yaml.safe_load(Path(path).read_text())
    return backend_from_config(config)
