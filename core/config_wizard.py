"""Interactive creation and editing of validated configuration profiles."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Any

from core.config_profiles import ConfigProfile, create_profile_id, validate_profile
from core.credential_probe import probe_provider_key, validate_provider_model_access
from core.credentials import (
    CLOUD_PROFILE_PROVIDERS,
    load_profile_api_key,
    save_profile_api_key,
    validate_api_key,
)

PROFILE_PROVIDERS = ["nvidia", "openai", "ollama", "local"]
PROFILE_MODES = ["chat", "agent"]
PROFILE_PERMISSIONS = ["ask", "auto"]


def _input_with_default(console: Any, label: str, default: str = "") -> str:
    prompt = f"{label} (Enter = {default})" if default else label
    entered = console.input(prompt).strip()
    return entered or default


def create_profile_interactively(
    console: Any,
    existing: ConfigProfile | None = None,
    *,
    profile_id: str | None = None,
    existing_profile_ids: Iterable[str] = (),
) -> ConfigProfile:
    """Collect, verify, and return one profile; persist its key only after validation."""
    while True:
        try:
            name = _input_with_default(console, "Название профиля", existing.name if existing else "")
            provider = console.choose(
                "Провайдер",
                PROFILE_PROVIDERS,
                default=existing.provider if existing else "nvidia",
            )
            same_provider = existing is not None and existing.provider == provider
            stable_id = profile_id or create_profile_id(name, existing_profile_ids)

            api_key = ""
            if provider in CLOUD_PROFILE_PROVIDERS:
                saved_key = (
                    load_profile_api_key(stable_id) if same_provider and profile_id is not None else ""
                )
                label = f"{provider.upper()} API key"
                if saved_key:
                    label += " (Enter = оставить сохранённый)"
                entered_key = console.secret(label).strip()
                api_key = validate_api_key(provider, entered_key or saved_key)

            model_default = existing.model if same_provider and existing is not None else ""
            model = _input_with_default(console, "Имя модели", model_default)
            mode = console.choose(
                "Режим",
                PROFILE_MODES,
                default=existing.mode if existing else "chat",
            )
            permissions = "ask"
            if mode == "agent":
                permissions = console.choose(
                    "Разрешения",
                    PROFILE_PERMISSIONS,
                    default=existing.permissions if existing else "ask",
                )
            # A new profile must receive every field explicitly.  Defaults are
            # reserved for editing so a blank answer cannot silently bind a new
            # profile to whichever directory happened to launch the process.
            project_default = existing.project_root if existing else ""
            project_root = str(
                Path(_input_with_default(console, "Рабочая папка", project_default))
                .expanduser()
                .resolve()
            )
            profile = validate_profile(
                ConfigProfile(
                    name=name,
                    provider=provider,
                    model=model,
                    mode=mode,
                    permissions=permissions,
                    project_root=project_root,
                )
            )

            if provider in CLOUD_PROFILE_PROVIDERS:
                console.activity(f"Проверка ключа и модели {provider.upper()}…")
                probe_provider_key(provider, api_key)
                validate_provider_model_access(provider, model, api_key)
                save_profile_api_key(stable_id, provider, api_key)

            console.success(
                f"Профиль проверен: {profile.name} · {profile.provider} · {profile.model}"
            )
            return profile
        except (EOFError, KeyboardInterrupt):
            raise
        except Exception as exc:
            console.error(str(exc))


__all__ = ["create_profile_interactively"]
