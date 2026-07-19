from main import SessionSettings, handle_slash, parse_slash


class FakeConsole:
    def __init__(self, choice: str = "", secret: str = "") -> None:
        self.choice = choice
        self.secret_value = secret
        self.messages: list[tuple[str, str]] = []

    def choose(self, _title: str, _options: list[str]) -> str:
        return self.choice

    def secret(self, _label: str) -> str:
        return self.secret_value

    def __getattr__(self, name: str):
        def record(message: str, *_args) -> None:
            self.messages.append((name, message))

        return record


class FakeSession:
    def clear(self) -> None:
        pass


def test_parse_slash_command_and_value():
    assert parse_slash("/provider gemini") == ("provider", "gemini")
    assert parse_slash("  /MODE agent  ") == ("mode", "agent")
    assert parse_slash("ordinary prompt") is None


def test_provider_command_resets_model_and_client(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "configured")
    settings = SessionSettings(provider="nvidia", model="custom")
    console = FakeConsole()
    client, should_exit = handle_slash(("provider", "gemini"), settings, console, FakeSession(), object())
    assert client is None
    assert should_exit is False
    assert settings.provider == "gemini"
    assert settings.model is None


def test_provider_command_can_use_interactive_choice():
    settings = SessionSettings()
    console = FakeConsole(choice="ollama")
    handle_slash(("provider", ""), settings, console, FakeSession(), None)
    assert settings.provider == "ollama"


def test_provider_command_prompts_for_missing_api_key(monkeypatch):
    saved: list[tuple[str, str]] = []
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setattr("main.save_api_key", lambda provider, key: saved.append((provider, key)))
    settings = SessionSettings(provider="nvidia")

    client, _ = handle_slash(
        ("provider", "gemini"), settings, FakeConsole(secret="secret-value"), FakeSession(), object()
    )

    assert saved == [("gemini", "secret-value")]
    assert settings.provider == "gemini"
    assert client is None


def test_provider_command_keeps_current_provider_when_key_is_empty(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    settings = SessionSettings(provider="nvidia")

    client, _ = handle_slash(
        ("provider", "gemini"), settings, FakeConsole(secret=""), FakeSession(), object()
    )

    assert settings.provider == "nvidia"
    assert client is not None


def test_provider_command_keeps_current_provider_when_key_cannot_be_saved(monkeypatch):
    def fail_save(_provider, _key):
        raise OSError("denied")

    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setattr("main.save_api_key", fail_save)
    settings = SessionSettings(provider="nvidia")

    client, _ = handle_slash(
        ("provider", "gemini"), settings, FakeConsole(secret="secret"), FakeSession(), object()
    )

    assert settings.provider == "nvidia"
    assert client is not None


def test_ollama_rejects_agent_mode():
    settings = SessionSettings(provider="ollama")
    console = FakeConsole()
    handle_slash(("mode", "agent"), settings, console, FakeSession(), None)
    assert settings.agent is False
    assert any(level == "error" for level, _ in console.messages)


def test_permissions_command_changes_policy():
    settings = SessionSettings()
    console = FakeConsole()
    handle_slash(("permissions", "auto"), settings, console, FakeSession(), None)
    assert settings.auto_approve is True
