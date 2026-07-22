"""Small, non-secret user preferences for the startup wizard."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from core.credentials import credentials_path


@dataclass(slots=True)
class UserPreferences:
    provider: str = "nvidia"
    mode: str = "chat"
    permissions: str = "ask"
    models: dict[str, str] = field(default_factory=dict)
    project_root: str = ""
    recent_projects: list[str] = field(default_factory=list)

    def remember_project(self, project_root: str, limit: int = 5) -> None:
        resolved = str(Path(project_root).expanduser().resolve())
        self.project_root = resolved
        self.recent_projects = [resolved, *(item for item in self.recent_projects if item != resolved)][
            :limit
        ]


def preferences_path() -> Path:
    return credentials_path().with_name("config.json")


def load_preferences(path: Path | None = None) -> UserPreferences:
    target = path or preferences_path()
    try:
        payload: dict[str, Any] = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError):
        return UserPreferences()

    provider = str(payload.get("provider", "nvidia"))
    mode = str(payload.get("mode", "chat"))
    permissions = str(payload.get("permissions", "ask"))
    raw_models = payload.get("models")
    models = (
        {str(name): str(model) for name, model in raw_models.items()} if isinstance(raw_models, dict) else {}
    )
    if provider not in {"nvidia", "gemini", "ollama"}:
        provider = "nvidia"
    if mode not in {"chat", "agent"}:
        mode = "chat"
    if permissions not in {"ask", "auto"}:
        permissions = "ask"
    return UserPreferences(
        provider=provider,
        mode=mode,
        permissions=permissions,
        models=models,
        project_root=str(payload.get("project_root", "")),
        recent_projects=[str(item) for item in payload.get("recent_projects", []) if isinstance(item, str)][
            :5
        ],
    )


def save_preferences(preferences: UserPreferences, path: Path | None = None) -> Path:
    target = path or preferences_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(asdict(preferences), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temporary.replace(target)
    return target


__all__ = ["UserPreferences", "load_preferences", "preferences_path", "save_preferences"]
