from core.runtime_config import response_temperature, response_token_limit


def test_response_limits_have_fast_safe_defaults(monkeypatch):
    monkeypatch.delenv("CITADEX_MAX_RESPONSE_TOKENS", raising=False)
    monkeypatch.delenv("CITADEX_TEMPERATURE", raising=False)
    assert response_token_limit() == 2048
    assert response_temperature() == 0.2


def test_response_limits_are_bounded(monkeypatch):
    monkeypatch.setenv("CITADEX_MAX_RESPONSE_TOKENS", "999999")
    monkeypatch.setenv("CITADEX_TEMPERATURE", "5")
    assert response_token_limit() == 8192
    assert response_temperature() == 1.0
