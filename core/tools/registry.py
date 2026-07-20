"""Central registration and dispatch for provider-neutral tools."""

from __future__ import annotations

from collections.abc import Callable
from time import perf_counter
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError, ValidationError

from core.tools.models import ToolCall, ToolDefinition, ToolError, ToolResult, ToolStatus
from core.tools.permissions import PermissionCallback, PermissionPolicy

ToolHandler = Callable[[dict[str, Any]], dict[str, Any]]


class ToolRegistry:
    """Own tool definitions and dispatch calls to their handlers."""

    def __init__(
        self,
        permission_policy: PermissionPolicy | None = None,
        permission_callback: PermissionCallback | None = None,
    ) -> None:
        self._definitions: dict[str, ToolDefinition] = {}
        self._handlers: dict[str, ToolHandler] = {}
        self._validators: dict[str, Draft202012Validator] = {}
        self._permission_policy = permission_policy
        self._permission_callback = permission_callback

    def register(self, definition: ToolDefinition, handler: ToolHandler) -> None:
        """Register one tool, rejecting ambiguous duplicate names."""
        if definition.name in self._definitions:
            raise ValueError(f"Tool is already registered: {definition.name}")
        if not callable(handler):
            raise TypeError("Tool handler must be callable.")
        try:
            Draft202012Validator.check_schema(definition.input_schema)
        except SchemaError as exc:
            raise ValueError(f"Invalid JSON Schema for tool {definition.name}: {exc.message}") from exc
        self._definitions[definition.name] = definition
        self._handlers[definition.name] = handler
        self._validators[definition.name] = Draft202012Validator(definition.input_schema)

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

        validation_error = self._first_validation_error(call)
        if validation_error is not None:
            path = ".".join(str(part) for part in validation_error.absolute_path)
            location = f"$.{path}" if path else "$"
            return ToolResult(
                call_id=call.id,
                name=call.name,
                status=ToolStatus.ERROR,
                error=ToolError(
                    code="INVALID_ARGUMENTS",
                    message=f"Invalid arguments at {location}: {validation_error.message}",
                    details={
                        "path": location,
                        "validator": str(validation_error.validator),
                    },
                ),
            )

        definition = self._definitions[call.name]
        if self._permission_policy is not None:
            permission_error = self._permission_policy.authorize(
                definition,
                call,
                self._permission_callback,
            )
            if permission_error is not None:
                return ToolResult(
                    call_id=call.id,
                    name=call.name,
                    status=ToolStatus.DENIED,
                    error=permission_error,
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

    def _first_validation_error(self, call: ToolCall) -> ValidationError | None:
        errors = self._validators[call.name].iter_errors(call.arguments)
        return next(
            iter(
                sorted(
                    errors,
                    key=lambda error: tuple(str(part) for part in error.absolute_path),
                )
            ),
            None,
        )


__all__ = ["ToolHandler", "ToolRegistry"]
