# <img src="assets/logo.svg" width="50" align="center" alt="logo"> strobe

**Process Mining & Agent Instrumentation for AI Agent Frameworks**

[![CI/CD Pipeline](https://github.com/edugonza/strobe/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/edugonza/strobe/actions/workflows/ci.yml)
[![PyPI Version](https://img.shields.io/pypi/v/strobe)](https://pypi.org/project/strobe/)
[![PyPI Downloads](https://img.shields.io/pypi/dm/strobe)](https://pypi.org/project/strobe/)
[![Python Version](https://img.shields.io/badge/python-3.13+-blue)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow)](https://opensource.org/licenses/MIT)


`strobe` is a Python package that instruments AI agent frameworks to capture execution events and analyze agent behavior using process mining techniques. It helps you understand, visualize, and optimize how your agents execute.

## Features

- 🎯 **Event Instrumentation**: Decorators and plugins to capture agent execution events (tool calls, LLM invocations, agent steps)
- 💾 **Pluggable Storage**: In-memory or PostgreSQL backends for event persistence (scale across agent replicas)
- 🔬 **Process Discovery**: Automatically discover process models from execution traces (Directly-Follows Graphs, Petri nets)
- 📊 **Performance Analysis**: Throughput times, activity statistics, and bottleneck detection
- ✅ **Conformance Checking**: Verify if agent behavior conforms to expected process specifications
- 📈 **Interactive Visualization**: Beautiful Plotly charts and Streamlit dashboard for exploring results
- 📁 **Standard Formats**: Export/import event logs in XES (eXtensible Event Stream) format

## Installation

### Requirements
- Python >= 3.13
- `uv` package manager (see [https://docs.astral.sh/uv/](https://docs.astral.sh/uv/))

### Setup

```bash
# Clone the repository
git clone <repository-url>
cd strobe

# Install dependencies (including test dependencies)
uv sync --group test

# Optional: Install PostgreSQL backend support
uv sync --extra postgres
```

## Quick Start

### 1. Instrument Your Agent

Use `StrobePlugin` to capture events from your agent framework:

```python
from strobe import StrobePlugin, PostgreSQLBackend
import asyncio

# Option A: In-memory backend (default, suitable for single agent)
plugin = StrobePlugin()

# Option B: PostgreSQL backend (for agent replicas sharing event logs)
async def setup_plugin():
    backend = PostgreSQLBackend("postgresql://user:pass@localhost/strobe")
    await backend.initialize()  # Create tables on first use
    plugin = StrobePlugin(backend=backend)
    return plugin

# Register with your agent framework (e.g., Google ADK)
# The plugin automatically captures:
# - Tool invocations
# - LLM calls
# - Agent steps
```

### 2. Discover Process Models

Analyze the captured events to discover how your agent actually behaves:

```python
from strobe import discover_dfg, discover_process_model
import asyncio

# Get the event log DataFrame (awaitable)
df = await log.to_dataframe()

# Extract a Directly-Follows Graph (DFG)
dfg, start_acts, end_acts = discover_dfg(df)

# Or discover a Petri net process model
net, initial_marking, final_marking = discover_process_model(df, method='inductive')
```

### 3. Visualize Results

Create interactive visualizations of discovered processes:

```python
from strobe import plot_dfg, plot_petri_net

# Plot the DFG with hierarchical flowchart layout
fig = plot_dfg(dfg, start_acts, end_acts)
fig.show()

# Plot the Petri net
fig = plot_petri_net(net, initial_marking, final_marking)
fig.show()
```

### 4. Analyze Performance

Get detailed performance metrics:

```python
from strobe import throughput_times, activity_statistics, plot_activity_statistics
import asyncio

# Get the event log DataFrame
df = await log.to_dataframe()

# Per-case throughput times
times = throughput_times(df)
print(f"Mean execution time: {times.mean()}")

# Per-activity statistics
stats = activity_statistics(df)
fig = plot_activity_statistics(stats)
fig.show()
```

### 5. Check Conformance

Verify if execution traces conform to a process model:

```python
from strobe import check_conformance
import asyncio

# Get the event log DataFrame
df = await log.to_dataframe()

# Token-based replay conformance checking
scores = check_conformance(df, net, initial_marking, final_marking)
print(f"Fitness: {scores['fitness']:.3f}")
print(f"Precision: {scores['precision']:.3f}")
print(f"Generalization: {scores['generalization']:.3f}")
print(f"Simplicity: {scores['simplicity']:.3f}")
```

### 6. Export and Launch Dashboard

Export your event log to XES format and explore in an interactive Streamlit dashboard:

```python
from strobe import launch_dashboard
import asyncio

# Export captured events to XES file
await log.write_xes("execution_log.xes")

# Launch dashboard to explore the log
proc = launch_dashboard(xes_path="execution_log.xes")
```

Or run the dashboard directly:
```bash
streamlit run strobe/visualization/app.py
```

Remember to clean up backend resources:
```python
await log.close()
```

## Architecture

strobe has four main layers:

### 1. Instrumentation (`strobe.instrumentation`)
Captures execution events from agent frameworks via callbacks/plugins:
- `StrobePlugin`: Integrates with agent framework (ADK BasePlugin)
- `EventLog`: Accumulates events and exports to DataFrame/XES (async interface)
- **Storage Backends**: Pluggable event persistence (in-memory, PostgreSQL)

### 2. Storage (`strobe.instrumentation.backends`)
Pluggable backends for event persistence:
- `InMemoryBackend`: In-process list storage (default, single-agent)
- `PostgreSQLBackend`: Shared PostgreSQL database (multi-agent, scalable)
- `StorageBackend`: Abstract interface for custom implementations

### 3. Analysis (`strobe.analysis`)
Process mining algorithms operating on event logs:
- **Discovery**: Extract Directly-Follows Graphs (DFG) and Petri nets
- **Performance**: Throughput times and activity statistics
- **Conformance**: Token-based replay conformance checking

### 4. Visualization (`strobe.visualization`)
Interactive charts and dashboards:
- **Plots**: Plotly figure factories (hierarchical flowcharts, Petri nets, statistics)
- **Dashboard**: Streamlit app for exploring results

### Module Structure

```
strobe/
├── __init__.py                  # Main API exports
├── instrumentation/
│   ├── event_log.py             # EventLog class (async interface)
│   ├── plugin.py                # StrobePlugin (ADK integration)
│   └── backends/
│       ├── __init__.py          # Backend exports
│       ├── base.py              # StorageBackend abstract class
│       ├── memory.py            # InMemoryBackend
│       └── postgresql.py        # PostgreSQLBackend
├── analysis/
│   ├── discovery.py             # Process discovery
│   ├── conformance.py           # Conformance checking
│   └── performance.py           # Performance analysis
└── visualization/
    ├── plots.py                 # Plotly figure factories
    └── app.py                   # Streamlit dashboard
```

## Storage Backends

By default, `EventLog` and `StrobePlugin` use an in-memory backend suitable for single-agent scenarios. For multi-agent setups or persistent logging, use the PostgreSQL backend:

### In-Memory Backend (Default)

```python
from strobe import EventLog

# EventLog automatically uses InMemoryBackend
log = EventLog()
await log.add_event(...)
```

**Use when:**
- Running a single agent instance
- Collecting events within a session
- Data doesn't need to persist across restarts

### PostgreSQL Backend

```python
from strobe import StrobePlugin, PostgreSQLBackend
import asyncio

async def setup():
    # Create backend and initialize database
    backend = PostgreSQLBackend(
        dsn="postgresql://user:password@localhost:5432/strobe_db",
        table="events"
    )
    await backend.initialize()  # Creates tables and indexes

    # Use with StrobePlugin
    plugin = StrobePlugin(backend=backend)
    # Or directly with EventLog
    # log = EventLog(backend=backend)

    # Clean up when done
    await plugin.event_log.close()

asyncio.run(setup())
```

**Use when:**
- Multiple agent replicas share event logs
- Need persistent event storage across sessions
- Analyzing long-running agent systems
- Querying events from external tools

**Environment:**
```bash
# Install PostgreSQL support
uv sync --extra postgres
```

**Database schema:**
```sql
CREATE TABLE strobe_events (
    id          BIGSERIAL PRIMARY KEY,
    case_id     TEXT        NOT NULL,
    activity    TEXT        NOT NULL,
    timestamp   TIMESTAMPTZ NOT NULL,
    attrs       JSONB       NOT NULL DEFAULT '{}'
);
CREATE INDEX idx_strobe_events_case_id   ON strobe_events(case_id);
CREATE INDEX idx_strobe_events_activity  ON strobe_events(activity);
CREATE INDEX idx_strobe_events_timestamp ON strobe_events(timestamp);
```

### StrobePlugin with Custom Backend

`StrobePlugin` accepts both `case_grouping` and a custom `backend` parameter:

```python
from strobe import StrobePlugin, PostgreSQLBackend

async def setup():
    backend = PostgreSQLBackend("postgresql://...")
    await backend.initialize()

    # Group events by invocation ID with PostgreSQL backend
    plugin = StrobePlugin(
        case_grouping="invocation",
        backend=backend
    )
    return plugin
```

### Custom Backends

Implement the `StorageBackend` interface to create custom backends:

```python
from strobe.instrumentation.backends import StorageBackend

class MyCustomBackend(StorageBackend):
    async def append_event(self, event: dict) -> None:
        # Store event somewhere
        pass

    async def get_events(self) -> list[dict]:
        # Retrieve all events
        pass

    async def close(self) -> None:
        # Cleanup resources
        pass

# Use with StrobePlugin or EventLog
plugin = StrobePlugin(backend=MyCustomBackend())
```

## API Reference

### Key Classes

| Name | Module | Purpose |
|------|--------|---------|
| `EventLog` | `strobe.instrumentation` | Buffer and export execution events (async interface) |
| `StrobePlugin` | `strobe.instrumentation` | ADK plugin for event capture |
| `StorageBackend` | `strobe.instrumentation.backends` | Abstract base class for storage implementations |
| `InMemoryBackend` | `strobe.instrumentation.backends` | In-memory event storage (default) |
| `PostgreSQLBackend` | `strobe.instrumentation.backends` | PostgreSQL event storage (optional, requires asyncpg) |

### Key Functions

| Name | Module | Returns |
|------|--------|---------|
| `discover_dfg` | `strobe.analysis` | `(dfg, start_acts, end_acts)` |
| `discover_process_model` | `strobe.analysis` | `(net, im, fm)` |
| `check_conformance` | `strobe.analysis` | `dict[str, float]` (fitness, precision, generalization, simplicity) |
| `throughput_times` | `strobe.analysis` | `pd.Series` |
| `activity_statistics` | `strobe.analysis` | `pd.DataFrame` |
| `plot_dfg` | `strobe.visualization` | `plotly.graph_objects.Figure` |
| `plot_petri_net` | `strobe.visualization` | `plotly.graph_objects.Figure` |
| `plot_activity_statistics` | `strobe.visualization` | `plotly.graph_objects.Figure` |
| `plot_conformance` | `strobe.visualization` | `plotly.graph_objects.Figure` |
| `launch_dashboard` | `strobe.visualization` | Process handle |

## Running Tests

```bash
# Run all tests
uv run pytest

# Run tests for a specific module
uv run pytest tests/analysis/
uv run pytest tests/instrumentation/
uv run pytest tests/visualization/

# Run a specific test file
uv run pytest tests/analysis/test_discovery.py

# Run tests matching a keyword
uv run pytest -k "discovery"

# Run with verbose output
uv run pytest -v
```

All tests pass (49 tests across instrumentation, analysis, and visualization layers).

### Testing Requirements

PostgreSQL backend tests use **testcontainers** to spin up a PostgreSQL container for testing. This requires:
- **Docker** to be running on your system
- **testcontainers** and **asyncpg** installed (included in test dependencies)

To skip PostgreSQL backend tests locally (when Docker is unavailable), run:
```bash
uv run pytest -k "not postgresql"
```

Or run only specific test suites:
```bash
uv run pytest tests/analysis/ tests/instrumentation/backends/test_memory_backend.py tests/visualization/
```

In CI/CD environments with Docker available, all 49 tests including PostgreSQL backend tests will run automatically.

## XES Event Log Format

Events are stored in XES (eXtensible Event Stream) format with the following attribute mapping:

| Concept | XES Attribute | Example |
|---------|---------------|---------|
| Invocation ID | `case:concept:name` | `"inv-abc123"` |
| Activity | `concept:name` | `"tool:search"`, `"llm:gemini-2.0"` |
| Completion time | `time:timestamp` | ISO datetime |
| Start time | `strobe:start_time` | ISO datetime |
| Duration | `strobe:duration_s` | `1.23` |
| Tool arguments | `strobe:tool_args` | JSON string |
| Tool result | `strobe:tool_result` | JSON string |
| Model name | `strobe:model_name` | `"gemini-2.0-flash"` |
| Input tokens | `strobe:input_tokens` | Integer count |
| Output tokens | `strobe:output_tokens` | Integer count |

## Supported Frameworks

Currently supports:
- Google AI Agent Development Kit (ADK)

## Dependencies

### Core
- **pm4py** >= 2.7.0 — Process mining algorithms
- **pandas** >= 2.0.0 — Data manipulation
- **networkx** — Graph algorithms
- **plotly** >= 5.18.0 — Interactive visualizations
- **streamlit** >= 1.32.0 — Dashboard UI
- **google-adk** >= 1.0.0 — Agent framework

### Optional
- **asyncpg** >= 0.30 — PostgreSQL async driver (install with `uv sync --extra postgres`)

## Contributing

Contributions are welcome! Please:
1. Write tests for any new functionality
2. Run `uv run pytest` to ensure tests pass
3. Follow existing code style and patterns

## License

(Add your license here)

## Badge Status

The following badges are currently displayed in this README:

| Badge | Purpose | Status |
|-------|---------|--------|
| ![CI/CD Pipeline](https://github.com/edugonza/strobe/actions/workflows/ci.yml/badge.svg?branch=main) | GitHub Actions CI/CD status on main branch | ✅ Active |
| ![PyPI Version](https://img.shields.io/pypi/v/strobe.svg) | Latest version on PyPI | 📦 When published |
| ![Python Version](https://img.shields.io/badge/python-3.13+-blue.svg) | Minimum Python version required | ✅ Static |
| ![License](https://img.shields.io/badge/License-MIT-yellow.svg) | License information | ⏳ Update with actual license |

### Suggested Additional Badges

Consider adding these badges when available:

## Resources

- [Process Mining Overview](https://en.wikipedia.org/wiki/Process_mining)
- [Petri Nets](https://en.wikipedia.org/wiki/Petri_net)
- [XES Standard](http://www.xes-standard.org/)
- [pm4py Documentation](https://pm4py.fit.fraunhofer.de/)
