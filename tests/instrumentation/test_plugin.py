"""Tests for StrobePlugin — ADK plugin that captures callbacks."""
import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from strobe.instrumentation.event_log import EventLog
from strobe.instrumentation.plugin import StrobePlugin


def _make_tool_context(invocation_id="inv-001", function_call_id="fc-1"):
    ctx = SimpleNamespace(
        invocation_id=invocation_id,
        function_call_id=function_call_id,
    )
    return ctx


def _make_callback_context(invocation_id="inv-001", agent_name="root_agent"):
    ctx = SimpleNamespace(
        invocation_id=invocation_id,
        agent_name=agent_name,
    )
    return ctx


def _make_tool(name="search"):
    return SimpleNamespace(name=name)


# ── tool callbacks ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_tool_event_recorded():
    plugin = StrobePlugin()
    tool = _make_tool("search")
    tool_args = {"query": "hello"}
    ctx = _make_tool_context()

    await plugin.before_tool_callback(tool, tool_args, ctx)
    await plugin.after_tool_callback(tool, tool_args, ctx, {"result": "ok"})

    df = plugin.to_dataframe()
    assert len(df) == 1
    assert df.iloc[0][EventLog.ACTIVITY] == "tool:search"
    assert df.iloc[0][EventLog.CASE_ID] == "inv-001"


@pytest.mark.asyncio
async def test_tool_event_has_duration():
    plugin = StrobePlugin()
    tool = _make_tool("search")
    ctx = _make_tool_context()

    await plugin.before_tool_callback(tool, {}, ctx)
    await plugin.after_tool_callback(tool, {}, ctx, {})

    df = plugin.to_dataframe()
    assert "strobe:duration_s" in df.columns
    assert df.iloc[0]["strobe:duration_s"] >= 0.0


@pytest.mark.asyncio
async def test_tool_event_has_args_and_result():
    plugin = StrobePlugin()
    tool = _make_tool("lookup")
    ctx = _make_tool_context()

    await plugin.before_tool_callback(tool, {"k": "v"}, ctx)
    await plugin.after_tool_callback(tool, {"k": "v"}, ctx, "result_value")

    df = plugin.to_dataframe()
    assert "strobe:tool_args" in df.columns
    assert "strobe:tool_result" in df.columns


@pytest.mark.asyncio
async def test_multiple_tool_calls_same_case():
    plugin = StrobePlugin()
    tool = _make_tool("search")

    ctx1 = _make_tool_context(function_call_id="fc-1")
    ctx2 = _make_tool_context(function_call_id="fc-2")

    await plugin.before_tool_callback(tool, {}, ctx1)
    await plugin.before_tool_callback(tool, {}, ctx2)
    await plugin.after_tool_callback(tool, {}, ctx1, {})
    await plugin.after_tool_callback(tool, {}, ctx2, {})

    df = plugin.to_dataframe()
    assert len(df) == 2
    assert (df[EventLog.CASE_ID] == "inv-001").all()


# ── LLM callbacks ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_llm_event_recorded():
    plugin = StrobePlugin()
    ctx = _make_callback_context()

    llm_request = SimpleNamespace()
    llm_response = SimpleNamespace(
        model="gemini-2.0-flash",
        usage_metadata=SimpleNamespace(
            prompt_token_count=100,
            candidates_token_count=50,
        ),
    )

    await plugin.before_model_callback(ctx, llm_request)
    await plugin.after_model_callback(ctx, llm_response)

    df = plugin.to_dataframe()
    assert len(df) == 1
    row = df.iloc[0]
    assert row[EventLog.ACTIVITY] == "llm:gemini-2.0-flash"
    assert row[EventLog.CASE_ID] == "inv-001"


@pytest.mark.asyncio
async def test_llm_event_tokens():
    plugin = StrobePlugin()
    ctx = _make_callback_context()

    llm_request = SimpleNamespace()
    llm_response = SimpleNamespace(
        model="gemini-2.0-flash",
        usage_metadata=SimpleNamespace(
            prompt_token_count=123,
            candidates_token_count=456,
        ),
    )

    await plugin.before_model_callback(ctx, llm_request)
    await plugin.after_model_callback(ctx, llm_response)

    df = plugin.to_dataframe()
    assert df.iloc[0]["strobe:input_tokens"] == 123
    assert df.iloc[0]["strobe:output_tokens"] == 456


# ── Agent callbacks ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_agent_event_recorded():
    plugin = StrobePlugin()
    ctx = _make_callback_context(agent_name="root_agent")

    await plugin.before_agent_callback(ctx)
    await plugin.after_agent_callback(ctx)

    df = plugin.to_dataframe()
    assert len(df) == 1
    assert df.iloc[0][EventLog.ACTIVITY] == "agent:root_agent"
    assert df.iloc[0][EventLog.CASE_ID] == "inv-001"


@pytest.mark.asyncio
async def test_agent_event_has_duration():
    plugin = StrobePlugin()
    ctx = _make_callback_context()

    await plugin.before_agent_callback(ctx)
    await plugin.after_agent_callback(ctx)

    df = plugin.to_dataframe()
    assert df.iloc[0]["strobe:duration_s"] >= 0.0


# ── Combined scenario ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_full_invocation_event_count():
    plugin = StrobePlugin()

    agent_ctx = _make_callback_context(invocation_id="inv-A", agent_name="root_agent")
    llm_ctx = _make_callback_context(invocation_id="inv-A")
    tool_ctx = _make_tool_context(invocation_id="inv-A", function_call_id="fc-1")
    tool = _make_tool("calculator")

    await plugin.before_agent_callback(agent_ctx)
    await plugin.before_model_callback(llm_ctx, SimpleNamespace())
    await plugin.after_model_callback(
        llm_ctx,
        SimpleNamespace(model="gemini", usage_metadata=None),
    )
    await plugin.before_tool_callback(tool, {}, tool_ctx)
    await plugin.after_tool_callback(tool, {}, tool_ctx, {})
    await plugin.after_agent_callback(agent_ctx)

    df = plugin.to_dataframe()
    assert len(df) == 3  # llm + tool + agent
    assert (df[EventLog.CASE_ID] == "inv-A").all()


# ── Property and export ──────────────────────────────────────────────────────

def test_event_log_property():
    plugin = StrobePlugin()
    assert isinstance(plugin.event_log, EventLog)


@pytest.mark.asyncio
async def test_write_xes(tmp_path):
    plugin = StrobePlugin()
    ctx = _make_tool_context()
    tool = _make_tool("search")

    await plugin.before_tool_callback(tool, {}, ctx)
    await plugin.after_tool_callback(tool, {}, ctx, {})

    xes_file = tmp_path / "out.xes"
    plugin.write_xes(xes_file)
    assert xes_file.exists()
    assert xes_file.stat().st_size > 0
