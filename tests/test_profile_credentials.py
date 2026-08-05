import os

import pytest
from dotenv import dotenv_values

from core.credentials import (
    delete_profile_api_key,
    load_profile_api_key,
    profile_key_name,
    save_profile_api_key,
)


def test_profile_key_name_is_stable_and_scoped():
    assert profile_key_name("nvidia-fast") == "CITADEX_PROFILE_NVIDIA_FAST_API_KEY"
    assert profile_key_name("openai-2") == "CITADEX_PROFILE_OPENAI_2_API_KEY"


@pytest.mark.parametrize("profile_id", ["", "NVIDIA Fast", "../secret", "profile_name"])
def test_profile_key_name_rejects_invalid_ids(profile_id):
    with pytest.raises(ValueError, match="profile ID"):
        profile_key_name(profile_id)


def test_profile_key_round_trip_uses_environment_and_credentials_file(tmp_path, monkeypatch):
    target = tmp_path / ".env"
    environment_name = profile_key_name("nvidia-fast")
    monkeypatch.delenv(environment_name, raising=False)

    result = save_profile_api_key("nvidia-fast", "nvidia", "  nvapi-secret  ", target)

    assert result == target
    assert dotenv_values(target)[environment_name] == "nvapi-secret"
    assert os.environ[environment_name] == "nvapi-secret"
    assert load_profile_api_key("nvidia-fast", target) == "nvapi-secret"
    assert "nvapi-secret" not in repr(result)


def test_profile_key_load_prefers_explicit_environment(tmp_path, monkeypatch):
    target = tmp_path / ".env"
    save_profile_api_key("openai-agent", "openai", "saved-key", target)
    monkeypatch.setenv(profile_key_name("openai-agent"), "explicit-key")

    assert load_profile_api_key("openai-agent", target) == "explicit-key"


def test_profile_key_can_be_deleted_without_returning_secret(tmp_path, monkeypatch):
    target = tmp_path / ".env"
    environment_name = profile_key_name("openai-agent")
    monkeypatch.delenv(environment_name, raising=False)
    save_profile_api_key("openai-agent", "openai", "very-secret", target)

    assert delete_profile_api_key("openai-agent", target) is True
    assert environment_name not in os.environ
    assert environment_name not in dotenv_values(target)


def test_nvidia_profile_key_keeps_prefix_validation(tmp_path):
    with pytest.raises(ValueError, match="nvapi-"):
        save_profile_api_key("nvidia-fast", "nvidia", "wrong-key", tmp_path / ".env")


@pytest.mark.parametrize("provider", ["ollama", "local"])
def test_local_providers_never_create_profile_key(provider, tmp_path, monkeypatch):
    target = tmp_path / ".env"
    environment_name = profile_key_name("local-profile")
    monkeypatch.delenv(environment_name, raising=False)

    assert save_profile_api_key("local-profile", provider, "unused", target) is None
    assert not target.exists()
    assert environment_name not in os.environ
    assert load_profile_api_key("local-profile", target) == ""
