"""Compatibility export for provider function schemas.

New code should consume ``BUILTIN_TOOL_DEFINITIONS`` or a ``ToolRegistry``.
"""

from typing import Any

from core.tool_protocol import TOOL_SCHEMAS

FUNCTION_DEFINITIONS: list[dict[str, Any]] = [schema["function"] for schema in TOOL_SCHEMAS]

__all__ = ["FUNCTION_DEFINITIONS"]
