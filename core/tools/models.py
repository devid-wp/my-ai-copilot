"""Provider-neutral contracts used by the tool-calling runtime."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ToolRisk(str, Enum):
    """Risk category used by permission policies before execution."""

    READ_ONLY = "read_only"
    PROJECT_WRITE = "project_write"
    PROJECT_DELETE = "project_delete"
    COMMAND_READ = "command_read"
    COMMAND_WRITE = "command_write"
    NETWORK = "network"
    DEPENDENCY_INSTALL = "dependency_install"
    GIT_DESTRUCTIVE = "git_destructive"


class ToolStatus(str, Enum):
    SUCCESS = "success"
    ERROR = "error"
    DENIED = "denied"


class AgentEventType(str, Enum):
    AGENT_STARTED = "agent_started"
    TEXT_DELTA = "text_delta"
    TOOL_CALL_RECEIVED = "tool_call_received"
    APPROVAL_REQUIRED = "approval_required"
    TOOL_STARTED = "tool_started"
    TOOL_COMPLETED = "tool_completed"
    AGENT_COMPLETED = "agent_completed"
    AGENT_FAILED = "agent_failed"


@dataclass(frozen=True, slots=True)
class ToolCall:
    """A complete tool request reconstructed from provider stream chunks."""

    id: str
    name: str
    arguments: dict[str, Any]

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise ValueError("Tool call id cannot be empty.")
        if not self.name.strip():
            raise ValueError("Tool name cannot be empty.")


@dataclass(frozen=True, slots=True)
class ToolError:
    code: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.code.strip():
            raise ValueError("Tool error code cannot be empty.")


@dataclass(frozen=True, slots=True)
class ToolResult:
    call_id: str
    name: str
    status: ToolStatus
    content: dict[str, Any] = field(default_factory=dict)
    error: ToolError | None = None
    duration_ms: int = 0

    def __post_init__(self) -> None:
        if not self.call_id.strip():
            raise ValueError("Tool result call_id cannot be empty.")
        if not self.name.strip():
            raise ValueError("Tool result name cannot be empty.")
        if self.duration_ms < 0:
            raise ValueError("Tool result duration cannot be negative.")
        if self.status is ToolStatus.SUCCESS and self.error is not None:
            raise ValueError("A successful tool result cannot contain an error.")
        if self.status is not ToolStatus.SUCCESS and self.error is None:
            raise ValueError("An error or denied tool result must contain ToolError.")


@dataclass(frozen=True, slots=True)
class ToolDefinition:
    name: str
    description: str
    input_schema: dict[str, Any]
    risk: ToolRisk

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("Tool definition name cannot be empty.")
        if not self.description.strip():
            raise ValueError("Tool definition description cannot be empty.")
        if self.input_schema.get("type") != "object":
            raise ValueError("Tool input schema must describe a JSON object.")

    def to_openai_schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.input_schema,
            },
        }


@dataclass(frozen=True, slots=True)
class ProviderCapabilities:
    native_tools: bool = False
    parallel_tools: bool = False
    streaming_tools: bool = False


@dataclass(frozen=True, slots=True)
class AgentEvent:
    type: AgentEventType
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class AgentLimits:
    max_steps: int = 30
    max_tool_calls: int = 100
    max_repeated_calls: int = 2
    max_consecutive_errors: int = 3
    max_output_chars: int = 20_000
    command_timeout_seconds: int = 30
    max_seconds: int = 300
    max_estimated_tokens: int = 32_000

    def __post_init__(self) -> None:
        for name in (
            "max_steps",
            "max_tool_calls",
            "max_repeated_calls",
            "max_consecutive_errors",
            "max_output_chars",
            "command_timeout_seconds",
            "max_seconds",
            "max_estimated_tokens",
        ):
            if getattr(self, name) <= 0:
                raise ValueError(f"{name} must be greater than zero.")
