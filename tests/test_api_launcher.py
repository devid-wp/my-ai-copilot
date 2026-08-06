import citadex_api


def test_configure_api_tests_tools_before_saving(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    events = []
    monkeypatch.setattr(citadex_api, "create_api_client", lambda *_args: object())
    monkeypatch.setattr(citadex_api, "check_native_tool_calling", lambda _client: events.append("tested"))
    monkeypatch.setattr(
        citadex_api, "save_profile_api_key", lambda *_args: events.append("saved-key")
    )
    monkeypatch.setattr(
        citadex_api, "save_active_profile", lambda *_args: events.append("saved-profile")
    )
    model = citadex_api.configure_api("openai", "secret", "gpt-5.6")
    assert model == "gpt-5.6"
    assert events == ["tested", "saved-key", "saved-profile"]


def test_launcher_allows_replacing_saved_key(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "old-key")
    monkeypatch.setattr(citadex_api, "choose_provider", lambda: "openai")
    monkeypatch.setattr(citadex_api, "load_profile_api_key", lambda _profile_id: "")
    monkeypatch.setattr(citadex_api, "getpass", lambda _label: "new-key")
    monkeypatch.setattr("builtins.input", lambda _label: "gpt-5.6")
    received = []
    monkeypatch.setattr(
        citadex_api,
        "configure_api",
        lambda provider, key, model: received.append((provider, key, model)) or model,
    )
    launched = []
    monkeypatch.setattr(citadex_api, "citadex_main", lambda args: launched.extend(args) or 0)
    assert citadex_api.run() == 0
    assert received == [("openai", "new-key", "gpt-5.6")]
    assert "--provider" not in launched
    assert "--model" not in launched


def test_configure_api_rejects_empty_model():
    try:
        citadex_api.configure_api("openai", "secret", "  ")
    except ValueError as exc:
        assert "модели" in str(exc)
    else:
        raise AssertionError("empty model must be rejected")
