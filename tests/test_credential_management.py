import os

from core.credentials import credential_status, delete_api_key, save_api_key


def test_credential_status_and_delete_never_return_secret(tmp_path, monkeypatch):
    target = tmp_path / ".env"
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    save_api_key("gemini", "very-secret", target)
    assert credential_status()["gemini"] is True
    assert "very-secret" not in repr(credential_status())
    assert delete_api_key("gemini", target) is True
    assert "GEMINI_API_KEY" not in os.environ
