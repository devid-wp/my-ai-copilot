import os

import pytest
from dotenv import dotenv_values

from core.credentials import load_credentials, save_api_key


def test_save_api_key_persists_and_updates_current_environment(tmp_path, monkeypatch):
    target = tmp_path / "config" / ".env"
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)

    result = save_api_key("nvidia", "  test-secret  ", target)

    assert result == target
    assert dotenv_values(target)["NVIDIA_API_KEY"] == "test-secret"
    assert os.environ["NVIDIA_API_KEY"] == "test-secret"


def test_save_api_key_preserves_other_credentials(tmp_path):
    target = tmp_path / ".env"
    save_api_key("nvidia", "nvidia-secret", target)
    save_api_key("gemini", "gemini-secret", target)

    values = dotenv_values(target)
    assert values["NVIDIA_API_KEY"] == "nvidia-secret"
    assert values["GEMINI_API_KEY"] == "gemini-secret"


def test_load_credentials_does_not_override_explicit_environment(tmp_path, monkeypatch):
    target = tmp_path / ".env"
    save_api_key("gemini", "saved-secret", target)
    monkeypatch.setenv("GEMINI_API_KEY", "explicit-secret")

    load_credentials(target)

    assert os.environ["GEMINI_API_KEY"] == "explicit-secret"


def test_save_api_key_rejects_unsupported_provider(tmp_path):
    with pytest.raises(ValueError, match="does not use"):
        save_api_key("ollama", "unused", tmp_path / ".env")
