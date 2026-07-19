"""Central registration and dispatch for provider-neutral tools."""

from __future__ import annotations

from collections.abc import Callable
from time import perf_counter
from typing import Any

from core.tools.models import ToolCall, ToolDefinition, ToolError, ToolResult, ToolStatus

ToolHandler = Callable[[dict[str, Any]], dict[str, Any]]


class ToolRegistry:
    """Own tool definitions and dispatch calls to their handlers."""

    def __init__(self) -> None:
        self._definitions: dict[str, ToolDefinition] = {}
        self._handlers: dict[str, ToolHandler] = {}

    def register(self, definition: ToolDefinition, handler: ToolHandler) -> None:
        """Register one tool, rejecting ambiguous duplicate names."""
        if definition.name in self._definitions:
            raise ValueError(f"Tool is already registered: {definition.name}")
        if not callable(handler):
            raise TypeError("Tool handler must be callable.")
        self._definitions[definition.name] = definition
        self._handlers[definition.name] = handler

    def get(self, name: str) -> ToolDefinition | None:
        return self._definitions.get(name)

    def definitions(self) -> tuple[ToolDefinition, ...]:
        """Return definitions in stable registration order."""
        return tuple(self._definitions.values())

    def openai_schemas(self) -> list[dict[str, Any]]:
        return [definition.to_openai_schema() for definition in self._definitions.values()]

    def execute(self, call: ToolCall) -> ToolResult:
        """Execute a call and convert normal handler failures into a result."""
        handler = self._handlers.get(call.name)
        if handler is None:
            return ToolResult(
                call_id=call.id,
                name=call.name,
                status=ToolStatus.ERROR,
                error=ToolError(
                    code="UNKNOWN_TOOL",
                    message=f"Tool is not registered: {call.name}",
                ),
            )

        started = perf_counter()
        try:
            content = handler(dict(call.arguments))
            if not isinstance(content, dict):
                raise TypeError("Tool handler must return a dictionary.")
            return ToolResult(
                call_id=call.id,
                name=call.name,
                status=ToolStatus.SUCCESS,
                content=content,
                duration_ms=self._elapsed_ms(started),
            )
        except Exception as exc:
            return ToolResult(
                call_id=call.id,
                name=call.name,
                status=ToolStatus.ERROR,
                error=ToolError(
                    code="TOOL_EXECUTION_FAILED",
                    message=str(exc) or type(exc).__name__,
                    details={"exception_type": type(exc).__name__},
                ),
                duration_ms=self._elapsed_ms(started),
            )

    @staticmethod
    def _elapsed_ms(started: float) -> int:
        return max(0, round((perf_counter() - started) * 1000))


__all__ = ["ToolHandler", "ToolRegistry"]
