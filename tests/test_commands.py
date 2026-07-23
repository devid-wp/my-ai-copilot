from core.tool_compatibility import ToolCompatibility
from main import SessionSettings, handle_slash, parse_slash, verify_tool_compatibility


class FakeConsole:
    def __init__(self, choice: str = "", secret: str = "", model_choice: str = "") -> None:
        self.choice = choice
        self.model_choice = model_choice
        self.secret_value = secret
        self.secret_prompts: list[str] = []
        self.messages: list[tuple[str, str]] = []

    def choose(self, title: str, _options: list[str]) -> str:
        if title == "Модель" and self.model_choice:
            return self.model_choice
        return self.choice

    def secret(self, label: str) -> str:
        self.secret_prompts.append(label)
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
    console = FakeConsole(model_choice="gemini-2.5-pro")
    client, should_exit = handle_slash(("provider", "gemini"), settings, console, FakeSession(), object())
    assert client is None
    assert should_exit is False
    assert settings.provider == "gemini"
    assert settings.model == "gemini-2.5-pro"
    assert console.secret_prompts == []


def test_provider_command_can_use_interactive_choice(monkeypatch):
    monkeypatch.setattr("main.provider_models", lambda _provider: ["qwen2.5:3b"])
    settings = SessionSettings()
    console = FakeConsole(choice="ollama", model_choice="qwen2.5:3b")
    handle_slash(("provider", ""), settings, console, FakeSession(), None)
    assert settings.provider == "ollama"
    assert settings.model == "qwen2.5:3b"


def test_ollama_model_menu_uses_installed_models(monkeypatch):
    monkeypatch.setattr(
        "main.provider_models",
        lambda _provider: ["qwen2.5:3b", "qwen2.5-coder:1.5b"],
    )
    settings = SessionSettings(provider="ollama")
    console = FakeConsole(choice="qwen2.5-coder:1.5b")

    client, _ = handle_slash(("model", ""), settings, console, FakeSession(), object())

    assert settings.model == "qwen2.5-coder:1.5b"
    assert client is None


def test_provider_command_prompts_for_missing_api_key(monkeypatch):
    saved: list[tuple[str, str]] = []
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setattr("main.save_api_key", lambda provider, key: saved.append((provider, key)))
    settings = SessionSettings(provider="nvidia")

    client, _ = handle_slash(
        ("provider", "gemini"),
        settings,
        FakeConsole(secret="secret-value", model_choice="gemini-2.0-flash"),
        FakeSession(),
        object(),
    )

    assert saved == [("gemini", "secret-value")]
    assert settings.provider == "gemini"
    assert client is None


def test_provider_command_reuses_saved_api_key(monkeypatch):
    saved: list[tuple[str, str]] = []
    monkeypatch.setenv("GEMINI_API_KEY", "old-key")
    monkeypatch.setattr("main.save_api_key", lambda provider, key: saved.append((provider, key)))
    settings = SessionSettings(provider="nvidia")

    handle_slash(
        ("provider", "gemini"),
        settings,
        FakeConsole(secret="new-key", model_choice="gemini-2.0-flash"),
        FakeSession(),
        object(),
    )

    assert saved == []
    assert settings.provider == "gemini"


def test_provider_command_rejects_invalid_nvidia_key(monkeypatch):
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    settings = SessionSettings(provider="gemini")
    console = FakeConsole(secret="wrong-key")

    client, _ = handle_slash(
        ("provider", "nvidia"), settings, console, FakeSession(), object()
    )

    assert settings.provider == "gemini"
    assert client is not None
    assert any("nvapi-" in message for level, message in console.messages if level == "error")


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


def test_ollama_allows_agent_mode(monkeypatch):
    monkeypatch.setattr("main.verify_tool_compatibility", lambda _settings, _console: True)
    settings = SessionSettings(provider="ollama")
    console = FakeConsole()
    handle_slash(("mode", "agent"), settings, console, FakeSession(), None)
    assert settings.agent is True


def test_ollama_rejects_agent_mode_when_model_is_incompatible(monkeypatch):
    monkeypatch.setattr("main.verify_tool_compatibility", lambda _settings, _console: False)
    settings = SessionSettings(provider="ollama", model="weak-model")

    handle_slash(("mode", "agent"), settings, FakeConsole(), FakeSession(), None)

    assert settings.agent is False


def test_cloud_agent_mode_requires_native_tool_support(monkeypatch):
    monkeypatch.setenv("NVIDIA_API_KEY", "nvapi-key")
    monkeypatch.setattr(
        "main.probe_cloud_tool_support",
        lambda *_args: ToolCompatibility.UNRELIABLE,
    )
    settings = SessionSettings(provider="nvidia", model="weak-model")

    assert verify_tool_compatibility(settings, FakeConsole()) is False
    assert settings.tool_compatibility == "unreliable"


def test_permissions_command_changes_policy():
    settings = SessionSettings()
    console = FakeConsole()
    handle_slash(("permissions", "auto"), settings, console, FakeSession(), None)
    assert settings.auto_approve is True


def test_project_command_changes_working_root_and_resets_client(tmp_path):
    settings = SessionSettings(project_root="C:/old-project")

    client, should_exit = handle_slash(
        ("project", str(tmp_path)), settings, FakeConsole(), FakeSession(), object()
    )

    assert settings.project_root == str(tmp_path.resolve())
    assert client is None
    assert should_exit is False


def test_project_command_rejects_missing_directory(tmp_path):
    settings = SessionSettings(project_root="C:/old-project")
    client_instance = object()

    client, _ = handle_slash(
        ("project", str(tmp_path / "missing")),
        settings,
        FakeConsole(),
        FakeSession(),
        client_instance,
    )

    assert settings.project_root == "C:/old-project"
    assert client is client_instance


def test_replacing_active_provider_key_resets_client_and_cached_check(monkeypatch):
    monkeypatch.setattr("main.configure_provider_key", lambda *_args, **_kwargs: True)
    cleared: list[str] = []
    monkeypatch.setattr("main.rate_limit_monitor.clear", cleared.append)
    settings = SessionSettings(provider="gemini")
    console = FakeConsole(choice="gemini")

    choices = iter(["gemini", "Заменить"])
    console.choose = lambda _title, _options: next(choices)
    client, _ = handle_slash(("keys", ""), settings, console, FakeSession(), object())

    assert client is None
    assert cleared == ["gemini"]
