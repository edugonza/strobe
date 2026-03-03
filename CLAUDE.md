# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

`strobe` is a Python package (requires Python >=3.13) managed with `uv`. It provides instrumentation methods
for recording execution events on different kinds of agent frameworks. Then it provides a set of tools to analyze
the recorded events and study the behavior of the agents. For that it makes use of process mining techniques such as
process discovery, process performance analysis, compliance and conformance analysis, and other process mining techniques.

## Commands

```bash
# Install dependencies (including test group)
uv sync --group test

# Install dev dependencies (includes linting, formatting, pre-commit)
uv sync --group dev

# Run all tests
uv run pytest

# Run a single test file
uv run pytest tests/path/to/test_file.py

# Run a single test by name
uv run pytest tests/path/to/test_file.py::test_name

# Run tests matching a keyword
uv run pytest -k "keyword"
```

## Pre-commit Hooks

Pre-commit hooks are configured to run automatically before each commit. Install them with:

```bash
pre-commit install
```

Hooks run:
- **ruff check**: Linting with Ruff (auto-fixes when possible)
- **ruff format**: Code formatting with Ruff
- **mypy**: Static type checking
- **Basic checks**: Trailing whitespace, end-of-file fixers, YAML/JSON validation, merge conflict detection

To run hooks manually on all files:

```bash
pre-commit run --all-files
```

## CI/CD

GitHub Actions workflows run the same checks on pull requests and pushes to `main`:
- `.github/workflows/ci.yml`: Runs linting, formatting, type checking, and tests

## Architecture

The library has three main layers:

- **Instrumentation** (`strobe.instrumentation`): decorators/hooks/callbacks that integrate with agent frameworks to capture execution events (e.g. tool calls, LLM invocations, agent steps) and record them as event logs.
- **Analysis** (`strobe.analysis`): process mining tools that operate on the recorded event logs — process discovery, performance analysis, conformance checking, and other process mining techniques.
- **Visualization** (`strobe.visualization`): interactive Plotly charts and a Streamlit dashboard for exploring analysis results.

### Module layout

```
strobe/
  __init__.py                        # re-exports StrobePlugin + key analysis/viz functions
  instrumentation/
    __init__.py                      # exports StrobePlugin, EventLog
    event_log.py                     # EventLog: internal buffer → DataFrame / XES
    plugin.py                        # StrobePlugin: ADK BasePlugin implementation
  analysis/
    __init__.py                      # exports discover_dfg, discover_process_model,
                                     #   check_conformance, throughput_times, activity_statistics
    discovery.py                     # DFG and Petri net discovery wrappers
    conformance.py                   # token-based replay conformance checking
    performance.py                   # throughput times, per-activity stats
  visualization/
    __init__.py                      # exports plot_* functions + launch_dashboard
    plots.py                         # pure Plotly figure factories (no Streamlit import)
    app.py                           # Streamlit dashboard + launch_dashboard()

tests/
  instrumentation/
    test_event_log.py
    test_plugin.py
  analysis/
    test_discovery.py
    test_conformance.py
    test_performance.py
  visualization/
    test_plots.py
```

### Key types

| Symbol | Module | Description |
|---|---|---|
| `EventLog` | `strobe.instrumentation.event_log` | Accumulates events; exports XES / DataFrame |
| `StrobePlugin` | `strobe.instrumentation.plugin` | ADK `BasePlugin`; records tool/LLM/agent callbacks |
| `discover_dfg` | `strobe.analysis.discovery` | Returns `(dfg, start_acts, end_acts)` |
| `discover_process_model` | `strobe.analysis.discovery` | Returns `(net, im, fm)`; supports inductive & alpha |
| `check_conformance` | `strobe.analysis.conformance` | Returns fitness/precision/generalization/simplicity |
| `throughput_times` | `strobe.analysis.performance` | Per-case duration `Series` |
| `activity_statistics` | `strobe.analysis.performance` | Per-activity count + duration stats `DataFrame` |
| `plot_dfg` | `strobe.visualization.plots` | Plotly DFG figure (nodes + weighted edges) |
| `plot_petri_net` | `strobe.visualization.plots` | Plotly Petri net figure (places/transitions) |
| `plot_throughput_times` | `strobe.visualization.plots` | Violin plot of case durations |
| `plot_activity_statistics` | `strobe.visualization.plots` | Dual-axis bar chart (count + mean duration) |
| `plot_conformance` | `strobe.visualization.plots` | Horizontal bar chart of 4 conformance metrics |
| `launch_dashboard` | `strobe.visualization.app` | Starts Streamlit dashboard via subprocess |

### Running the dashboard

```bash
# Direct
streamlit run strobe/visualization/app.py

# From Python (programmatic, e.g. after saving a XES file)
from strobe import launch_dashboard
proc = launch_dashboard(xes_path="path/to/log.xes")
```

### XES event attribute mapping

| ADK concept | XES attribute | Example |
|---|---|---|
| `invocation_id` | `case:concept:name` | `"inv-abc123"` |
| activity | `concept:name` | `"tool:search"`, `"llm:gemini-2.0"`, `"agent:root_agent"` |
| completion time | `time:timestamp` | `datetime(...)` |
| start time | `strobe:start_time` | ISO string |
| wall-clock duration | `strobe:duration_s` | `1.23` |
| tool args | `strobe:tool_args` | JSON string |
| tool result | `strobe:tool_result` | JSON string |
| model name | `strobe:model_name` | `"gemini-2.0-flash"` |
| tokens in/out | `strobe:input_tokens`, `strobe:output_tokens` | `123`, `456` |
