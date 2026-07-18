from main import SessionSettings, handle_slash, parse_slash


class FakeConsole:
    def __init__(self, choice: str = "") -> None:
        self.choice = choice
        self.messages: list[tuple[str, str]] = []

    def choose(self, _title: str, _options: list[str]) -> str:
        return self.choice

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


def test_provider_command_resets_model_and_client():
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
