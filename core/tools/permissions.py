"""Central permission decisions for tool execution."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum

from core.tools.models import ToolCall, ToolDefinition, ToolError, ToolRisk


class PermissionMode(str, Enum):
    ASK = "ask"
    AUTO = "auto"
    READ_ONLY = "read-only"


@dataclass(frozen=True, slots=True)
class PermissionRequest:
    tool_name: str
    risk: ToolRisk
    action: str
    detail: str


PermissionCallback = Callable[[PermissionRequest], bool]

SAFE_RISKS = {ToolRisk.READ_ONLY, ToolRisk.COMMAND_READ}

RISK_ACTIONS = {
    ToolRisk.PROJECT_WRITE: "modify project files",
    ToolRisk.PROJECT_DELETE: "delete project files",
    ToolRisk.COMMAND_WRITE: "execute command",
    ToolRisk.NETWORK: "access network",
    ToolRisk.DEPENDENCY_INSTALL: "install dependencies",
    ToolRisk.GIT_DESTRUCTIVE: "perform destructive git action",
}


@dataclass(frozen=True, slots=True)
class PermissionPolicy:
    mode: PermissionMode = PermissionMode.ASK

    def authorize(
        self,
        definition: ToolDefinition,
        call: ToolCall,
        callback: PermissionCallback | None = None,
    ) -> ToolError | None:
        """Return an error when a call is denied, otherwise allow execution."""
        if definition.risk in SAFE_RISKS:
            return None
        if self.mode is PermissionMode.AUTO:
            return None

        request = PermissionRequest(
            tool_name=definition.name,
            risk=definition.risk,
            action=RISK_ACTIONS.get(definition.risk, "execute tool"),
            detail=_call_detail(call),
        )
        if self.mode is PermissionMode.ASK and callback is not None and callback(request):
            return None

        reason = (
            "The current permission mode is read-only."
            if self.mode is PermissionMode.READ_ONLY
            else "User approval was not granted."
        )
        return ToolError(
            code="PERMISSION_DENIED",
            message=f"{definition.name} was denied. {reason}",
            details={
                "risk": definition.risk.value,
                "mode": self.mode.value,
            },
        )


def _call_detail(call: ToolCall) -> str:
    """Describe a call for confirmation without exposing file content."""
    if call.arguments.get("path") is not None:
        return str(call.arguments["path"] or ".")
    if call.arguments.get("command") is not None:
        return str(call.arguments["command"])
    return call.name


__all__ = [
    "PermissionCallback",
    "PermissionMode",
    "PermissionPolicy",
    "PermissionRequest",
]
