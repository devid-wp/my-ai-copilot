"""Compatibility export for provider function schemas.

New code should consume ``BUILTIN_TOOL_DEFINITIONS`` or a ``ToolRegistry``.
"""

from typing import Any

from core.tools import BUILTIN_TOOL_DEFINITIONS

FUNCTION_DEFINITIONS: list[dict[str, Any]] = [
    definition.to_openai_schema()["function"] for definition in BUILTIN_TOOL_DEFINITIONS
]

__all__ = ["FUNCTION_DEFINITIONS"]
