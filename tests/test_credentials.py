import os

import pytest
from dotenv import dotenv_values

from core.credentials import load_credentials, save_api_key, validate_api_key


def test_save_api_key_persists_and_updates_current_environment(tmp_path, monkeypatch):
    target = tmp_path / "config" / ".env"
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)

    result = save_api_key("nvidia", "  nvapi-test-secret  ", target)

    assert result == target
    assert dotenv_values(target)["NVIDIA_API_KEY"] == "nvapi-test-secret"
    assert os.environ["NVIDIA_API_KEY"] == "nvapi-test-secret"


def test_save_api_key_preserves_other_credentials(tmp_path):
    target = tmp_path / ".env"
    save_api_key("nvidia", "nvapi-nvidia-secret", target)
    save_api_key("openai", "openai-secret", target)

    values = dotenv_values(target)
    assert values["NVIDIA_API_KEY"] == "nvapi-nvidia-secret"
    assert values["OPENAI_API_KEY"] == "openai-secret"


def test_load_credentials_does_not_override_explicit_environment(tmp_path, monkeypatch):
    target = tmp_path / ".env"
    save_api_key("openai", "saved-secret", target)
    monkeypatch.setenv("OPENAI_API_KEY", "explicit-secret")

    load_credentials(target)

    assert os.environ["OPENAI_API_KEY"] == "explicit-secret"


def test_save_api_key_rejects_unsupported_provider(tmp_path):
    with pytest.raises(ValueError, match="does not use"):
        save_api_key("ollama", "unused", tmp_path / ".env")


def test_validate_api_key_rejects_wrong_nvidia_key_format():
    with pytest.raises(ValueError, match="nvapi-"):
        validate_api_key("nvidia", "not-an-nvidia-key")


def test_validate_api_key_accepts_openai_key_without_prefix_requirement():
    assert validate_api_key("openai", "openai-key") == "openai-key"
