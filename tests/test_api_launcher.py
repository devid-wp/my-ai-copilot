import citadex_api


def test_configure_api_tests_tools_before_saving(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    events = []
    monkeypatch.setattr(citadex_api, "create_api_client", lambda *_args: object())
    monkeypatch.setattr(citadex_api, "check_native_tool_calling", lambda _client: events.append("tested"))
    monkeypatch.setattr(citadex_api, "save_api_key", lambda *_args: events.append("saved"))
    monkeypatch.setattr(citadex_api, "save_preferences", lambda _prefs: events.append("preferences"))
    model = citadex_api.configure_api("gemini", "secret")
    assert model == "gemini-2.5-pro"
    assert events == ["tested", "saved", "preferences"]
