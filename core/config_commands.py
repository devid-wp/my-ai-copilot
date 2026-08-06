"""Interactive profile management for the `/config` command."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Protocol

from core.config_profiles import (
    ConfigProfile,
    ProfileStore,
    create_profile_id,
    delete_profile,
    save_profile_store,
    set_active_profile,
    validate_profile,
)
from core.config_wizard import create_profile_interactively
from core.credential_probe import probe_provider_key, validate_provider_model_access
from core.credentials import (
    CLOUD_PROFILE_PROVIDERS,
    delete_profile_api_key,
    load_profile_api_key,
    save_profile_api_key,
    validate_api_key,
)

ACTIONS = [
    "Выбрать профиль",
    "Создать профиль",
    "Изменить профиль",
    "Проверить профиль",
    "Удалить профиль",
    "Отмена",
]


class SessionSettingsLike(Protocol):
    provider: str
    model: str | None
    agent: bool
    auto_approve: bool
    tool_compatibility: str
    project_root: str
    api_key: str


def _profile_labels(store: ProfileStore) -> dict[str, str]:
    return {
        f"{profile.name} · {profile.provider} · {profile.model} [{profile_id}]": profile_id
        for profile_id, profile in store.profiles.items()
    }


def _choose_profile_id(console: Any, store: ProfileStore) -> str:
    labels = _profile_labels(store)
    if not labels:
        raise ValueError("Нет сохранённых профилей.")
    default = next(
        (label for label, profile_id in labels.items() if profile_id == store.active_profile),
        None,
    )
    selected = console.choose("Профиль", list(labels), default=default)
    return labels[selected]


def _apply_profile(
    settings: SessionSettingsLike,
    profile: ConfigProfile,
    api_key: str,
) -> None:
    settings.provider = profile.provider
    settings.model = profile.model
    settings.agent = profile.mode == "agent"
    settings.auto_approve = profile.permissions == "auto"
    settings.tool_compatibility = "unknown"
    settings.project_root = profile.project_root
    settings.api_key = api_key


def _show_active(console: Any, profile: ConfigProfile) -> None:
    console.success(
        f"Профиль активен: {profile.name} · {profile.provider} · {profile.model} · {profile.mode}"
    )


def _activate(
    profile_id: str,
    working: ProfileStore,
    store: ProfileStore,
    settings: SessionSettingsLike,
    console: Any,
) -> None:
    profile = set_active_profile(working, profile_id)
    save_profile_store(working)
    store.version = working.version
    store.active_profile = working.active_profile
    store.profiles = dict(working.profiles)
    store.recent_projects = list(working.recent_projects)
    _apply_profile(settings, profile, load_profile_api_key(profile_id))
    _show_active(console, profile)


def _verify_profile(profile_id: str, store: ProfileStore, console: Any) -> None:
    profile = validate_profile(store.profiles[profile_id])
    if profile.provider in CLOUD_PROFILE_PROVIDERS:
        api_key = validate_api_key(profile.provider, load_profile_api_key(profile_id))
        console.activity(f"Проверка ключа и модели {profile.provider.upper()}…")
        probe_provider_key(profile.provider, api_key)
        validate_provider_model_access(profile.provider, profile.model, api_key)
    console.success(
        f"Профиль проверен: {profile.name} · {profile.provider} · {profile.model} · {profile.mode}"
    )


def handle_config_command(
    value: str,
    store: ProfileStore,
    settings: SessionSettingsLike,
    console: Any,
    client: Any | None,
) -> Any | None:
    """Manage profiles and return the current or reset LLM client."""
    if value:
        if value not in store.profiles:
            console.error(f"Неизвестный профиль: {value}")
            return client
        try:
            _activate(value, deepcopy(store), store, settings, console)
        except Exception as exc:
            console.error(str(exc))
            return client
        return None

    action = console.choose("Конфигурация", ACTIONS, default=ACTIONS[0])
    if action == "Отмена":
        return client

    try:
        if action == "Выбрать профиль":
            profile_id = _choose_profile_id(console, store)
            _activate(profile_id, deepcopy(store), store, settings, console)
            return None

        if action == "Создать профиль":
            profile = create_profile_interactively(
                console,
                existing_profile_ids=store.profiles,
            )
            profile_id = create_profile_id(profile.name, store.profiles)
            working = deepcopy(store)
            working.profiles[profile_id] = profile
            try:
                _activate(profile_id, working, store, settings, console)
            except Exception:
                delete_profile_api_key(profile_id)
                raise
            return None

        profile_id = _choose_profile_id(console, store)
        if action == "Изменить профиль":
            previous = store.profiles[profile_id]
            previous_key = load_profile_api_key(profile_id)
            profile = create_profile_interactively(
                console,
                previous,
                profile_id=profile_id,
            )
            working = deepcopy(store)
            working.profiles[profile_id] = profile
            try:
                _activate(profile_id, working, store, settings, console)
            except Exception:
                if previous.provider in CLOUD_PROFILE_PROVIDERS and previous_key:
                    save_profile_api_key(profile_id, previous.provider, previous_key)
                else:
                    delete_profile_api_key(profile_id)
                raise
            if profile.provider not in CLOUD_PROFILE_PROVIDERS:
                delete_profile_api_key(profile_id)
            return None

        if action == "Проверить профиль":
            _verify_profile(profile_id, store, console)
            return client

        if action == "Удалить профиль":
            profile = store.profiles[profile_id]
            if profile_id == store.active_profile and not console.confirm(
                "Удалить активный профиль?",
                profile.name,
            ):
                return client
            working = deepcopy(store)
            delete_profile(working, profile_id)
            replacement_id: str | None = None
            if not working.profiles:
                replacement = create_profile_interactively(
                    console,
                    existing_profile_ids=working.profiles,
                )
                replacement_id = create_profile_id(replacement.name, working.profiles)
                working.profiles[replacement_id] = replacement
                working.active_profile = replacement_id
            active_id = working.active_profile or next(iter(working.profiles))
            try:
                _activate(active_id, working, store, settings, console)
            except Exception:
                if replacement_id is not None:
                    delete_profile_api_key(replacement_id)
                raise
            delete_profile_api_key(profile_id)
            return None
    except (EOFError, KeyboardInterrupt):
        raise
    except Exception as exc:
        console.error(str(exc))
        return client

    console.error(f"Неизвестное действие: {action}")
    return client


__all__ = ["ACTIONS", "handle_config_command"]
