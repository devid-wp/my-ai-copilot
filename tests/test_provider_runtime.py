import httpx

from core.provider_runtime import explain_provider_error, provider_max_retries, provider_timeout


def test_provider_runtime_limits_are_configurable_and_bounded(monkeypatch):
    monkeypatch.setenv("CITADEX_CONNECT_TIMEOUT", "3")
    monkeypatch.setenv("CITADEX_FIRST_TOKEN_TIMEOUT", "12")
    monkeypatch.setenv("CITADEX_PROVIDER_RETRIES", "99")
    timeout = provider_timeout()
    assert isinstance(timeout, httpx.Timeout)
    assert timeout.connect == 3
    assert timeout.read == 12
    assert provider_max_retries() == 2


def test_provider_errors_are_explained():
    assert "отведённое время" in explain_provider_error(TimeoutError("timed out"), "NVIDIA")
    assert "лимит" in explain_provider_error(RuntimeError("429 rate limit"), "Gemini")
    assert "/keys" in explain_provider_error(RuntimeError("invalid API key"), "Gemini")
    assert "интернет" in explain_provider_error(RuntimeError("connection failed"), "NVIDIA")
