"""State and safety limits for a single agent run."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from time import perf_counter
from typing import Any

from core.tools import AgentLimits, ToolCall, ToolError, ToolResult, ToolStatus


@dataclass(frozen=True, slots=True)
class ToolRunRecord:
    name: str
    status: ToolStatus
    detail: str


@dataclass(slots=True)
class AgentLoopGuard:
    limits: AgentLimits
    tool_call_count: int = 0
    consecutive_errors: int = 0
    records: list[ToolRunRecord] = field(default_factory=list)
    _call_counts: dict[str, int] = field(default_factory=dict)
    _failed_calls: set[str] = field(default_factory=set)
    estimated_tokens: int = 0
    _started_at: float = field(default_factory=perf_counter)

    @property
    def elapsed_seconds(self) -> float:
        return perf_counter() - self._started_at

    def count_text(self, text: str) -> None:
        self.estimated_tokens += max(1, len(text) // 4)

    def budget_error(self) -> ToolError | None:
        if self.elapsed_seconds >= self.limits.max_seconds:
            return ToolError(code="TIME_BUDGET", message=f"Time budget reached ({self.limits.max_seconds}s).")
        if self.estimated_tokens >= self.limits.max_estimated_tokens:
            return ToolError(
                code="TOKEN_BUDGET",
                message=f"Estimated token budget reached ({self.limits.max_estimated_tokens}).",
            )
        return None

    def inspect(self, call: ToolCall) -> ToolError | None:
        """Count a call and reject it when a configured limit is exceeded."""
        exhausted = self.budget_error()
        if exhausted is not None:
            return exhausted
        if self.tool_call_count >= self.limits.max_tool_calls:
            return ToolError(
                code="TOOL_CALL_LIMIT",
                message=f"Tool call limit reached ({self.limits.max_tool_calls}).",
            )

        self.tool_call_count += 1
        signature = json.dumps(
            {"name": call.name, "arguments": call.arguments},
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        if signature in self._failed_calls:
            return ToolError(
                code="RETRY_WITHOUT_CHANGE",
                message="The same tool call already failed; change the arguments or approach.",
            )
        count = self._call_counts.get(signature, 0) + 1
        self._call_counts[signature] = count
        if count > self.limits.max_repeated_calls:
            return ToolError(
                code="REPEATED_TOOL_CALL",
                message=(f"Blocked repeated call to {call.name}; limit is {self.limits.max_repeated_calls}."),
            )
        return None

    def record(self, call: ToolCall, result: ToolResult) -> None:
        self.records.append(
            ToolRunRecord(
                name=call.name,
                status=result.status,
                detail=_call_detail(call.arguments),
            )
        )
        if result.status is ToolStatus.SUCCESS:
            self.consecutive_errors = 0
        else:
            self.consecutive_errors += 1
            self._failed_calls.add(
                json.dumps(
                    {"name": call.name, "arguments": call.arguments},
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                )
            )

    def record_invalid_call(self, name: str) -> None:
        self.records.append(ToolRunRecord(name=name or "unknown", status=ToolStatus.ERROR, detail=""))
        self.consecutive_errors += 1

    @property
    def error_limit_reached(self) -> bool:
        return self.consecutive_errors >= self.limits.max_consecutive_errors


def recovery_advice(code: str, project_root: str) -> str:
    """Return a concrete next action without leaking tool internals."""
    if code == "PATH_OUTSIDE_PROJECT":
        return f"Выберите нужную рабочую папку через /project <path> (сейчас: {project_root})."
    if code == "UNKNOWN_TOOL":
        return "Выберите модель с поддержкой native tool calling."
    if code in {"REPEATED_TOOL_CALL", "RETRY_WITHOUT_CHANGE"}:
        return "Измените аргументы или способ выполнения; одинаковый вызов повторён не будет."
    return "Проверьте входные данные инструмента и повторите запрос с исправленными параметрами."


def pseudo_tool_name(response: str) -> str | None:
    """Detect a strict JSON pseudo-call without ever executing it."""
    text = response.strip()
    if text.startswith("```") and text.endswith("```"):
        text = text[3:-3].strip()
        if text.casefold().startswith("json"):
            text = text[4:].lstrip()
    try:
        payload = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(payload, dict) or set(payload) != {"name", "arguments"}:
        return None
    if not isinstance(payload.get("name"), str) or not isinstance(payload.get("arguments"), dict):
        return None
    return payload["name"]


def _call_detail(arguments: dict[str, Any]) -> str:
    if arguments.get("path") is not None:
        return str(arguments["path"] or ".")
    if arguments.get("command") is not None:
        return str(arguments["command"])
    if arguments.get("destination") is not None:
        return str(arguments["destination"])
    return ""


__all__ = ["AgentLoopGuard", "ToolRunRecord", "pseudo_tool_name", "recovery_advice"]
