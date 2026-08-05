import json
from dataclasses import asdict

import pytest

from core.config_profiles import (
    ConfigProfile,
    ProfileStore,
    create_profile_id,
    delete_profile,
    get_active_profile,
    load_profile_store,
    save_profile_store,
    set_active_profile,
    validate_profile,
)


def profile(tmp_path, *, name="NVIDIA Fast", provider="nvidia"):
    return ConfigProfile(
        name=name,
        provider=provider,
        model="z-ai/glm-5.2" if provider == "nvidia" else "gpt-5-nano",
        mode="chat",
        permissions="ask",
        project_root=str(tmp_path),
    )


def test_profile_store_round_trip_is_atomic(tmp_path):
    target = tmp_path / "config.json"
    item = profile(tmp_path)
    store = ProfileStore(active_profile="nvidia-fast", profiles={"nvidia-fast": item})

    result = save_profile_store(store, target)

    assert result == target
    assert load_profile_store(target) == store
    assert not target.with_suffix(".tmp").exists()
    assert json.loads(target.read_text(encoding="utf-8"))["version"] == 2


def test_missing_store_loads_empty_version_two_store(tmp_path):
    assert load_profile_store(tmp_path / "missing.json") == ProfileStore()


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ({"version": 1, "profiles": {}}, "version"),
        ({"version": 2, "profiles": []}, "profiles"),
        ({"version": 2, "active_profile": "missing", "profiles": {}}, "active"),
    ],
)
def test_invalid_store_is_rejected(tmp_path, payload, message):
    target = tmp_path / "config.json"
    target.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match=message):
        load_profile_store(target)


def test_create_profile_id_is_stable_and_unique():
    assert create_profile_id("NVIDIA Fast") == "nvidia-fast"
    assert create_profile_id("NVIDIA Fast", {"nvidia-fast"}) == "nvidia-fast-2"
    assert create_profile_id("Профиль", {"profile", "profile-2"}) == "profile-3"


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"name": ""}, "name"),
        ({"provider": "gemini"}, "provider"),
        ({"model": ""}, "model"),
        ({"mode": "turbo"}, "mode"),
        ({"permissions": "always"}, "permissions"),
        ({"project_root": "missing"}, "project_root"),
    ],
)
def test_validate_profile_rejects_invalid_fields(tmp_path, changes, message):
    values = asdict(profile(tmp_path)) | changes

    with pytest.raises(ValueError, match=message):
        validate_profile(ConfigProfile(**values))


def test_active_profile_can_be_selected_and_deleted(tmp_path):
    first = profile(tmp_path)
    second = profile(tmp_path, name="OpenAI", provider="openai")
    store = ProfileStore(profiles={"nvidia": first, "openai": second})

    assert set_active_profile(store, "openai") is second
    assert get_active_profile(store) is second
    assert delete_profile(store, "openai") is second
    assert store.active_profile == "nvidia"
    assert get_active_profile(store) is first


def test_unknown_profile_operations_are_rejected():
    store = ProfileStore()

    with pytest.raises(KeyError, match="missing"):
        set_active_profile(store, "missing")
    with pytest.raises(KeyError, match="missing"):
        delete_profile(store, "missing")
