from core.tool_compatibility import ToolCompatibility
from main import SessionSettings, handle_slash, parse_slash, verify_tool_compatibility


class FakeConsole:
    def __init__(self, choice=""):
        self.choice = choice
        self.messages = []

    def choose(self, _title, _options, default=None):
        return self.choice or default or ""

    def __getattr__(self, name):
        def record(message, *_args):
            self.messages.append((name, message))

        return record


class FakeSession:
    def clear(self):
        pass


def test_parse_slash_command_and_value():
    assert parse_slash("/config openai-work") == ("config", "openai-work")
    assert parse_slash("  /MODE agent  ") == ("mode", "agent")
    assert parse_slash("ordinary prompt") is None


def test_removed_configuration_commands_are_unknown():
    console = FakeConsole()
    settings = SessionSettings()

    for command in ("keys", "provider", "model"):
        client = object()
        returned, should_exit = handle_slash(
            (command, ""), settings, console, FakeSession(), client
        )
        assert returned is client
        assert should_exit is False

    assert all(level == "error" for level, _message in console.messages)


def test_mode_change_resets_client_to_rebuild_optimized_prompt():
    settings = SessionSettings(provider="ollama", model="model")

    client, _ = handle_slash(
        ("mode", "chat"), settings, FakeConsole(), FakeSession(), object()
    )

    assert client is None


def test_agent_mode_requires_native_tool_support(monkeypatch):
    monkeypatch.setattr("main.verify_tool_compatibility", lambda *_args: False)
    settings = SessionSettings(provider="ollama", model="weak-model")

    handle_slash(("mode", "agent"), settings, FakeConsole(), FakeSession(), None)

    assert settings.agent is False


def test_cloud_agent_mode_uses_profile_key(monkeypatch):
    received = []
    monkeypatch.setattr(
        "main.probe_cloud_tool_support",
        lambda *args: received.append(args) or ToolCompatibility.SUPPORTED,
    )
    settings = SessionSettings(
        provider="nvidia",
        model="tool-model",
        api_key="profile-key",
    )

    assert verify_tool_compatibility(settings, FakeConsole()) is True
    assert received == [("nvidia", "tool-model", "profile-key")]


def test_permissions_command_changes_session_policy():
    settings = SessionSettings()
    handle_slash(("permissions", "auto"), settings, FakeConsole(), FakeSession(), None)
    assert settings.auto_approve is True


def test_project_command_changes_only_session_root_and_resets_client(tmp_path):
    settings = SessionSettings(project_root="C:/old-project")

    client, should_exit = handle_slash(
        ("project", str(tmp_path)), settings, FakeConsole(), FakeSession(), object()
    )

    assert settings.project_root == str(tmp_path.resolve())
    assert client is None
    assert should_exit is False


def test_project_command_rejects_missing_directory(tmp_path):
    settings = SessionSettings(project_root="C:/old-project")
    current_client = object()

    client, _ = handle_slash(
        ("project", str(tmp_path / "missing")),
        settings,
        FakeConsole(),
        FakeSession(),
        current_client,
    )

    assert settings.project_root == "C:/old-project"
    assert client is current_client
