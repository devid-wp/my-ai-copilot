"""Structured session diagnostics rendered by the CLI status command."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SessionDiagnostics:
    provider: str
    provider_state: str
    model: str
    model_state: str
    tools_state: str
    mode: str
    permissions: str
    project_root: str
    message_count: int
    client_state: str
    ollama_state: str = "unknown"


__all__ = ["SessionDiagnostics"]
