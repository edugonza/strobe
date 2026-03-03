try:
    from strobe._version import __version__
except ImportError:
    __version__ = "0.0.1.dev0"

from strobe.analysis import (
    activity_statistics,
    check_conformance,
    discover_dfg,
    discover_process_model,
    throughput_times,
)
from strobe.instrumentation import EventLog, StrobePlugin
from strobe.visualization import launch_dashboard

__all__ = [
    "__version__",
    "StrobePlugin",
    "EventLog",
    "discover_dfg",
    "discover_process_model",
    "check_conformance",
    "throughput_times",
    "activity_statistics",
    "launch_dashboard",
]
