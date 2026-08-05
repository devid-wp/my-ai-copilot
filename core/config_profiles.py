"""Versioned, non-secret configuration profiles for Citadex."""

from __future__ import annotations

import json
import re
import unicodedata
from collections.abc import Iterable
from contextlib import suppress
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from core.preferences import preferences_path

PROFILE_STORE_VERSION = 2
SUPPORTED_PROVIDERS = {"nvidia", "openai", "ollama", "local"}
SUPPORTED_MODES = {"chat", "agent"}
SUPPORTED_PERMISSIONS = {"ask", "auto"}


@dataclass(frozen=True, slots=True)
class ConfigProfile:
    name: str
    provider: str
    model: str
    mode: str = "chat"
    permissions: str = "ask"
    project_root: str = ""


@dataclass(slots=True)
class ProfileStore:
    version: int = PROFILE_STORE_VERSION
    active_profile: str | None = None
    profiles: dict[str, ConfigProfile] = field(default_factory=dict)
    recent_projects: list[str] = field(default_factory=list)


def create_profile_id(name: str, existing: Iterable[str] = ()) -> str:
    """Create a readable unique ID without exposing profile data in credentials."""
    ascii_name = (
        unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii").casefold()
    )
    base = re.sub(r"[^a-z0-9]+", "-", ascii_name).strip("-") or "profile"
    occupied = set(existing)
    candidate = base
    suffix = 2
    while candidate in occupied:
        candidate = f"{base}-{suffix}"
        suffix += 1
    return candidate


def validate_profile(profile: ConfigProfile) -> ConfigProfile:
    """Validate one profile and return it for convenient composition."""
    if not profile.name.strip():
        raise ValueError("profile name cannot be empty")
    if profile.provider not in SUPPORTED_PROVIDERS:
        raise ValueError(f"unsupported profile provider: {profile.provider}")
    if not profile.model.strip():
        raise ValueError("profile model cannot be empty")
    if profile.mode not in SUPPORTED_MODES:
        raise ValueError(f"unsupported profile mode: {profile.mode}")
    if profile.permissions not in SUPPORTED_PERMISSIONS:
        raise ValueError(f"unsupported profile permissions: {profile.permissions}")
    if not profile.project_root.strip() or not Path(profile.project_root).expanduser().is_dir():
        raise ValueError(f"profile project_root is not a directory: {profile.project_root}")
    return profile


def _validate_store(store: ProfileStore) -> ProfileStore:
    if store.version != PROFILE_STORE_VERSION:
        raise ValueError(f"unsupported profile store version: {store.version}")
    for profile_id, profile in store.profiles.items():
        if not profile_id.strip():
            raise ValueError("profile ID cannot be empty")
        validate_profile(profile)
    if store.active_profile is not None and store.active_profile not in store.profiles:
        raise ValueError(f"active profile does not exist: {store.active_profile}")
    return store


def _profile_from_payload(profile_id: str, payload: object) -> ConfigProfile:
    if not isinstance(payload, dict):
        raise ValueError(f"profile must be an object: {profile_id}")
    try:
        profile = ConfigProfile(
            name=str(payload["name"]),
            provider=str(payload["provider"]),
            model=str(payload["model"]),
            mode=str(payload.get("mode", "chat")),
            permissions=str(payload.get("permissions", "ask")),
            project_root=str(payload["project_root"]),
        )
    except KeyError as exc:
        raise ValueError(f"profile {profile_id} is missing field: {exc.args[0]}") from exc
    return validate_profile(profile)


def load_profile_store(path: Path | None = None) -> ProfileStore:
    """Load and validate the versioned profile store."""
    target = path or preferences_path()
    if not target.is_file():
        return ProfileStore()
    try:
        payload: Any = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"could not read profile store: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError("profile store must be a JSON object")
    version = payload.get("version")
    if version != PROFILE_STORE_VERSION:
        raise ValueError(f"unsupported profile store version: {version}")
    raw_profiles = payload.get("profiles", {})
    if not isinstance(raw_profiles, dict):
        raise ValueError("profiles must be a JSON object")
    recent = payload.get("recent_projects", [])
    if not isinstance(recent, list) or not all(isinstance(item, str) for item in recent):
        raise ValueError("recent_projects must be a list of strings")
    active = payload.get("active_profile")
    if active is not None and not isinstance(active, str):
        raise ValueError("active_profile must be a string or null")
    store = ProfileStore(
        version=version,
        active_profile=active,
        profiles={
            str(profile_id): _profile_from_payload(str(profile_id), item)
            for profile_id, item in raw_profiles.items()
        },
        recent_projects=list(recent),
    )
    return _validate_store(store)


def save_profile_store(store: ProfileStore, path: Path | None = None) -> Path:
    """Validate and atomically persist profiles without credential data."""
    _validate_store(store)
    target = path or preferences_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(".tmp")
    payload = {
        "version": store.version,
        "active_profile": store.active_profile,
        "profiles": {
            profile_id: asdict(profile) for profile_id, profile in store.profiles.items()
        },
        "recent_projects": store.recent_projects,
    }
    try:
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary.replace(target)
    except OSError:
        with suppress(OSError):
            temporary.unlink()
        raise
    return target


def get_active_profile(store: ProfileStore) -> ConfigProfile | None:
    if store.active_profile is None:
        return None
    return store.profiles.get(store.active_profile)


def set_active_profile(store: ProfileStore, profile_id: str) -> ConfigProfile:
    try:
        profile = store.profiles[profile_id]
    except KeyError:
        raise KeyError(f"unknown profile: {profile_id}") from None
    store.active_profile = profile_id
    return profile


def delete_profile(store: ProfileStore, profile_id: str) -> ConfigProfile:
    try:
        profile = store.profiles.pop(profile_id)
    except KeyError:
        raise KeyError(f"unknown profile: {profile_id}") from None
    if store.active_profile == profile_id:
        store.active_profile = next(iter(store.profiles), None)
    return profile


__all__ = [
    "ConfigProfile",
    "PROFILE_STORE_VERSION",
    "ProfileStore",
    "create_profile_id",
    "delete_profile",
    "get_active_profile",
    "load_profile_store",
    "save_profile_store",
    "set_active_profile",
    "validate_profile",
]
