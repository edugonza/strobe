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

# Run all tests
uv run pytest

# Run a single test file
uv run pytest tests/path/to/test_file.py

# Run a single test by name
uv run pytest tests/path/to/test_file.py::test_name

# Run tests matching a keyword
uv run pytest -k "keyword"
```

## Architecture

The library has two main layers:

- **Instrumentation** (`strobe.instrumentation`): decorators/hooks/callbacks that integrate with agent frameworks to capture execution events (e.g. tool calls, LLM invocations, agent steps) and record them as event logs.
- **Analysis** (`strobe.analysis`): process mining tools that operate on the recorded event logs — process discovery, performance analysis, conformance checking, and other process mining techniques.
