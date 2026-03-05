from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Literal

import pandas as pd
from google.adk import Context
from google.adk.plugins.base_plugin import BasePlugin

from .event_log import EventLog


class StrobePlugin(BasePlugin):
    """ADK plugin that captures tool, LLM, and agent callbacks as XES events."""

    def __init__(
        self, case_grouping: Literal["session", "invocation"] = "session"
    ) -> None:
        super().__init__(name="strobe")
        self._log = EventLog()
        self._pending: dict[tuple, datetime] = {}
        self._case_grouping = case_grouping

    # ── Tool callbacks ──────────────────────────────────────────────────────

    async def before_tool_callback(self, tool, tool_args, tool_context):
        key = (tool_context.invocation_id, tool_context.function_call_id)
        self._pending[key] = datetime.now(timezone.utc)

    def _get_case_id(self, context: Context):
        if self._case_grouping == "session":
            return context.session.id
        else:
            return context.invocation_id

    async def after_tool_callback(self, tool, tool_args, tool_context, tool_response):
        key = (tool_context.invocation_id, tool_context.function_call_id)
        start = self._pending.pop(key, None)
        now = datetime.now(timezone.utc)
        duration = (now - start).total_seconds() if start is not None else None

        attrs: dict = {}
        if start is not None:
            attrs["start_time"] = start.isoformat()
        if duration is not None:
            attrs["duration_s"] = duration
        try:
            attrs["tool_args"] = json.dumps(tool_args)
        except (TypeError, ValueError):
            attrs["tool_args"] = str(tool_args)
        try:
            attrs["tool_result"] = json.dumps(tool_response)
        except (TypeError, ValueError):
            attrs["tool_result"] = str(tool_response)

        self._log.add_event(
            case_id=self._get_case_id(tool_context),
            activity=f"tool:{tool.name}",
            timestamp=now,
            **attrs,
        )

    # ── LLM callbacks ───────────────────────────────────────────────────────

    async def before_model_callback(self, callback_context, llm_request):
        key = (callback_context.invocation_id, "llm")
        self._pending[key] = datetime.now(timezone.utc)

    async def after_model_callback(self, callback_context, llm_response):
        key = (callback_context.invocation_id, "llm")
        start = self._pending.pop(key, None)
        now = datetime.now(timezone.utc)
        duration = (now - start).total_seconds() if start is not None else None

        model_name = getattr(llm_response, "model", None) or getattr(
            llm_response, "model_version", None
        )

        attrs: dict = {}
        if start is not None:
            attrs["start_time"] = start.isoformat()
        if duration is not None:
            attrs["duration_s"] = duration
        if model_name:
            attrs["model_name"] = str(model_name)

        usage = getattr(llm_response, "usage_metadata", None)
        if usage is not None:
            input_tokens = getattr(usage, "prompt_token_count", None)
            output_tokens = getattr(usage, "candidates_token_count", None)
            if input_tokens is not None:
                attrs["input_tokens"] = input_tokens
            if output_tokens is not None:
                attrs["output_tokens"] = output_tokens

        activity = f"llm:{model_name}" if model_name else "llm"
        self._log.add_event(
            case_id=self._get_case_id(callback_context),
            activity=activity,
            timestamp=now,
            **attrs,
        )

    # ── Agent callbacks ──────────────────────────────────────────────────────

    async def before_agent_callback(self, callback_context):
        agent_name = getattr(callback_context, "agent_name", "unknown")
        key = (callback_context.invocation_id, f"agent:{agent_name}")
        self._pending[key] = datetime.now(timezone.utc)

    async def after_agent_callback(self, callback_context):
        agent_name = getattr(callback_context, "agent_name", "unknown")
        key = (callback_context.invocation_id, f"agent:{agent_name}")
        start = self._pending.pop(key, None)
        now = datetime.now(timezone.utc)
        duration = (now - start).total_seconds() if start is not None else None

        attrs: dict = {}
        if start is not None:
            attrs["start_time"] = start.isoformat()
        if duration is not None:
            attrs["duration_s"] = duration

        self._log.add_event(
            case_id=self._get_case_id(callback_context),
            activity=f"agent:{agent_name}",
            timestamp=now,
            **attrs,
        )

    # ── Export ───────────────────────────────────────────────────────────────

    @property
    def event_log(self) -> EventLog:
        return self._log

    def to_dataframe(self) -> pd.DataFrame:
        return self._log.to_dataframe()

    def write_xes(self, path) -> None:
        self._log.write_xes(path)
