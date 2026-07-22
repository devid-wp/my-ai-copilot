from main import SessionSettings, session_diagnostics


class Session:
    session_path = "C:/project/logs/session.json"

    def __init__(self):
        self.reloaded = False

    def reload(self):
        self.reloaded = True

    def get_history(self):
        return [{"role": "user"}, {"role": "assistant"}]


def test_ollama_diagnostics_report_model_and_tools(monkeypatch):
    monkeypatch.setattr("main.provider_models", lambda _provider: ["qwen2.5:3b"])
    settings = SessionSettings(
        provider="ollama",
        model="qwen2.5:3b",
        agent=True,
        tool_compatibility="supported",
        project_root="C:/project",
    )
    session = Session()

    diagnostics = session_diagnostics(settings, session, object())

    assert diagnostics.provider_state == "online"
    assert diagnostics.model_state == "available"
    assert diagnostics.tools_state == "supported"
    assert diagnostics.message_count == 2
    assert diagnostics.client_state == "initialized"
    assert diagnostics.ollama_state == "online"
    assert session.reloaded is True


def test_cloud_diagnostics_report_missing_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    settings = SessionSettings(provider="gemini", model="gemini-test", project_root="C:/project")

    diagnostics = session_diagnostics(settings, Session(), None)

    assert diagnostics.provider_state == "missing key"
    assert diagnostics.tools_state == "supported"
    assert diagnostics.client_state == "not started"
