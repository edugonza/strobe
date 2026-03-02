# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

`strobe` is a Python package (requires Python >=3.13) managed with `uv`.

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

# Install the package in editable mode
uv pip install -e .
```
