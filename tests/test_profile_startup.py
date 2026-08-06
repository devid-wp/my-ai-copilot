from core.config_profiles import ConfigProfile, ProfileStore
from main import main, settings_from_profile


class StartupConsole:
    def __init__(self, *_args, **_kwargs):
        self.errors = []

    def error(self, message):
        self.errors.append(message)

    def __getattr__(self, _name):
        return lambda *_args, **_kwargs: None


def profile(tmp_path, **changes):
    values = {
        "name": "OpenAI work",
        "provider": "openai",
        "model": "gpt-5.6",
        "mode": "chat",
        "permissions": "ask",
        "project_root": str(tmp_path),
    }
    values.update(changes)
    return ConfigProfile(**values)


def test_session_settings_are_created_from_profile(tmp_path):
    settings = settings_from_profile(
        profile(tmp_path, mode="agent", permissions="auto"),
        "profile-secret",
    )

    assert settings.provider == "openai"
    assert settings.model == "gpt-5.6"
    assert settings.agent is True
    assert settings.auto_approve is True
    assert settings.project_root == str(tmp_path)
    assert settings.api_key == "profile-secret"


def test_first_launch_creates_profile_before_building_client(tmp_path, monkeypatch):
    created = profile(tmp_path)
    saved = []
    clients = []
    monkeypatch.setattr("main.Console", StartupConsole)
    monkeypatch.setattr("main.load_profile_store", lambda: ProfileStore())
    monkeypatch.setattr("main.create_profile_interactively", lambda _console: created)
    monkeypatch.setattr("main.save_profile_store", lambda store: saved.append(store))
    monkeypatch.setattr("main.load_profile_api_key", lambda profile_id: f"key:{profile_id}")
    monkeypatch.setattr(
        "main.create_client",
        lambda selected, api_key, _prompt: clients.append(
            (selected.provider, selected.model, api_key)
        )
        or object(),
    )
    monkeypatch.setattr("main.run_chat", lambda *_args: None)

    assert main(["--oneshot", "hello"]) == 0

    assert saved[0].active_profile == "openai-work"
    assert saved[0].profiles == {"openai-work": created}
    assert clients == [("openai", "gpt-5.6", "key:openai-work")]


def test_cli_overrides_do_not_rewrite_active_profile(tmp_path, monkeypatch):
    active = profile(tmp_path)
    store = ProfileStore(active_profile="work", profiles={"work": active})
    clients = []
    monkeypatch.setenv("NVIDIA_API_KEY", "automation-key")
    monkeypatch.setattr("main.Console", StartupConsole)
    monkeypatch.setattr("main.load_profile_store", lambda: store)
    monkeypatch.setattr("main.load_profile_api_key", lambda _profile_id: "profile-key")
    monkeypatch.setattr(
        "main.create_client",
        lambda selected, api_key, _prompt: clients.append(
            (selected.provider, selected.model, api_key)
        )
        or object(),
    )
    monkeypatch.setattr("main.run_chat", lambda *_args: None)

    result = main(
        ["--oneshot", "hello", "--provider", "nvidia", "--model", "automation-model"]
    )

    assert result == 0
    assert store.profiles["work"] is active
    assert clients == [("nvidia", "automation-model", "automation-key")]


def test_repeat_interactive_launch_shows_active_profile_quick_start(tmp_path, monkeypatch):
    active = profile(tmp_path)
    store = ProfileStore(active_profile="work", profiles={"work": active})
    shown = []

    class RepeatConsole(StartupConsole):
        def quick_start(self, *args):
            shown.append(args)
            return True

        def prompt(self):
            return "exit"

    monkeypatch.setattr("main.Console", RepeatConsole)
    monkeypatch.setattr("main.load_profile_store", lambda: store)
    monkeypatch.setattr("main.load_profile_api_key", lambda _profile_id: "profile-key")

    assert main([]) == 0
    assert shown == [
        (
            "OpenAI work",
            "openai",
            "gpt-5.6",
            "chat",
            "ask",
            str(tmp_path),
        )
    ]


def test_repeat_agent_launch_does_not_probe_provider(tmp_path, monkeypatch):
    active = profile(tmp_path, mode="agent")
    store = ProfileStore(active_profile="work", profiles={"work": active})

    class AgentConsole(StartupConsole):
        def quick_start(self, *_args):
            return True

        def prompt(self):
            return "exit"

    monkeypatch.setattr("main.Console", AgentConsole)
    monkeypatch.setattr("main.load_profile_store", lambda: store)
    monkeypatch.setattr("main.load_profile_api_key", lambda _profile_id: "profile-key")
    monkeypatch.setattr(
        "main.verify_tool_compatibility",
        lambda *_args: (_ for _ in ()).throw(AssertionError("unexpected provider probe")),
    )

    assert main([]) == 0
