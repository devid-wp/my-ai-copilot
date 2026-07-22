"""Single provider-neutral tool schema and call normalization boundary."""

from __future__ import annotations

import json
from typing import Any

from core.tools import BUILTIN_TOOL_DEFINITIONS, ToolCall

TOOL_SCHEMAS: list[dict[str, Any]] = [definition.to_openai_schema() for definition in BUILTIN_TOOL_DEFINITIONS]


def normalize_tool_call(raw: dict[str, Any], fallback_id: str = "call_0") -> ToolCall:
    function = raw.get("function") or {}
    arguments = function.get("arguments", {})
    if isinstance(arguments, str):
        arguments = json.loads(arguments or "{}")
    return ToolCall(
        id=str(raw.get("id") or fallback_id),
        name=str(function.get("name") or raw.get("name") or ""),
        arguments=dict(arguments),
    )


def provider_tool_schemas() -> list[dict[str, Any]]:
    """Return fresh schema dictionaries so adapters cannot mutate global state."""
    return json.loads(json.dumps(TOOL_SCHEMAS))


__all__ = ["TOOL_SCHEMAS", "normalize_tool_call", "provider_tool_schemas"]
