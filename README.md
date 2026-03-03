# strobe

**Process Mining & Agent Instrumentation for AI Agent Frameworks**

`strobe` is a Python package that instruments AI agent frameworks to capture execution events and analyze agent behavior using process mining techniques. It helps you understand, visualize, and optimize how your agents execute.

## Features

- 🎯 **Event Instrumentation**: Decorators and plugins to capture agent execution events (tool calls, LLM invocations, agent steps)
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
```

## Quick Start

### 1. Instrument Your Agent

Use `StrobePlugin` to capture events from your agent framework:

```python
from strobe import StrobePlugin, EventLog

# Create a plugin and event log
plugin = StrobePlugin(event_log=EventLog())

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

# Extract a Directly-Follows Graph (DFG)
dfg, start_acts, end_acts = discover_dfg(event_log)

# Or discover a Petri net process model
net, initial_marking, final_marking = discover_process_model(event_log, method='inductive')
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

# Per-case throughput times
times = throughput_times(event_log)
print(f"Mean execution time: {times.mean()}")

# Per-activity statistics
stats = activity_statistics(event_log)
fig = plot_activity_statistics(stats)
fig.show()
```

### 5. Check Conformance

Verify if execution traces conform to a process model:

```python
from strobe import check_conformance

# Token-based replay conformance checking
scores = check_conformance(event_log, net, initial_marking, final_marking)
print(f"Fitness: {scores['fitness']:.3f}")
print(f"Precision: {scores['precision']:.3f}")
print(f"Generalization: {scores['generalization']:.3f}")
print(f"Simplicity: {scores['simplicity']:.3f}")
```

### 6. Launch Interactive Dashboard

View and explore your analysis results in an interactive Streamlit dashboard:

```python
from strobe import launch_dashboard

# Launch dashboard and serve a saved XES log
proc = launch_dashboard(xes_path="path/to/execution_log.xes")
```

Or run it directly:
```bash
streamlit run strobe/visualization/app.py
```

## Architecture

strobe has three main layers:

### 1. Instrumentation (`strobe.instrumentation`)
Captures execution events from agent frameworks via callbacks/plugins:
- `StrobePlugin`: Integrates with agent framework (ADK BasePlugin)
- `EventLog`: Accumulates events and exports to DataFrame/XES

### 2. Analysis (`strobe.analysis`)
Process mining algorithms operating on event logs:
- **Discovery**: Extract Directly-Follows Graphs (DFG) and Petri nets
- **Performance**: Throughput times and activity statistics
- **Conformance**: Token-based replay conformance checking

### 3. Visualization (`strobe.visualization`)
Interactive charts and dashboards:
- **Plots**: Plotly figure factories (hierarchical flowcharts, Petri nets, statistics)
- **Dashboard**: Streamlit app for exploring results

### Module Structure

```
strobe/
├── __init__.py                  # Main API exports
├── instrumentation/
│   ├── event_log.py             # EventLog class
│   └── plugin.py                # StrobePlugin (ADK integration)
├── analysis/
│   ├── discovery.py             # Process discovery
│   ├── conformance.py           # Conformance checking
│   └── performance.py           # Performance analysis
└── visualization/
    ├── plots.py                 # Plotly figure factories
    └── app.py                   # Streamlit dashboard
```

## API Reference

### Key Classes

| Name | Module | Purpose |
|------|--------|---------|
| `EventLog` | `strobe.instrumentation` | Buffer and export execution events |
| `StrobePlugin` | `strobe.instrumentation` | ADK plugin for event capture |

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

All tests pass (44 tests across instrumentation, analysis, and visualization layers).

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

- **pm4py** >= 2.7.0 — Process mining algorithms
- **pandas** >= 2.0.0 — Data manipulation
- **networkx** — Graph algorithms
- **plotly** >= 5.18.0 — Interactive visualizations
- **streamlit** >= 1.32.0 — Dashboard UI
- **google-adk** >= 1.0.0 — Agent framework

## Contributing

Contributions are welcome! Please:
1. Write tests for any new functionality
2. Run `uv run pytest` to ensure tests pass
3. Follow existing code style and patterns

## License

(Add your license here)

## Resources

- [Process Mining Overview](https://en.wikipedia.org/wiki/Process_mining)
- [Petri Nets](https://en.wikipedia.org/wiki/Petri_net)
- [XES Standard](http://www.xes-standard.org/)
- [pm4py Documentation](https://pm4py.fit.fraunhofer.de/)
