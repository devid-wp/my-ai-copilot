from core.config_commands import handle_config_command
from core.config_profiles import ConfigProfile, ProfileStore
from main import SessionSettings


class ConfigConsole:
    def __init__(self, choices=None, confirmed=True):
        self.choices = iter(choices or [])
        self.confirmed = confirmed
        self.messages = []

    def choose(self, *_args, **_kwargs):
        return next(self.choices)

    def confirm(self, *_args):
        return self.confirmed

    def __getattr__(self, name):
        return lambda message, *_args: self.messages.append((name, message))


def make_profile(tmp_path, name, provider="openai", model="gpt-5.6", mode="chat"):
    return ConfigProfile(
        name=name,
        provider=provider,
        model=model,
        mode=mode,
        permissions="ask",
        project_root=str(tmp_path),
    )


def test_config_argument_switches_profile_and_resets_client(tmp_path, monkeypatch):
    first = make_profile(tmp_path, "First")
    second = make_profile(tmp_path, "Second", provider="nvidia", model="nvidia-model", mode="agent")
    store = ProfileStore(active_profile="first", profiles={"first": first, "second": second})
    settings = SessionSettings()
    monkeypatch.setattr("core.config_commands.save_profile_store", lambda _store: None)
    monkeypatch.setattr("core.config_commands.load_profile_api_key", lambda profile_id: f"key:{profile_id}")

    client = handle_config_command("second", store, settings, ConfigConsole(), object())

    assert client is None
    assert store.active_profile == "second"
    assert (settings.provider, settings.model, settings.mode) == (
        "nvidia",
        "nvidia-model",
        "agent",
    )
    assert settings.api_key == "key:second"


def test_config_edits_profile_in_place_and_keeps_stable_id(tmp_path, monkeypatch):
    old = make_profile(tmp_path, "Old")
    edited = make_profile(tmp_path, "Renamed", model="gpt-new")
    store = ProfileStore(active_profile="stable-id", profiles={"stable-id": old})
    settings = SessionSettings()
    label = "Old · openai · gpt-5.6 [stable-id]"
    console = ConfigConsole(["Изменить профиль", label])
    received = []
    monkeypatch.setattr(
        "core.config_commands.create_profile_interactively",
        lambda _console, existing, **kwargs: received.append((existing, kwargs)) or edited,
    )
    monkeypatch.setattr("core.config_commands.save_profile_store", lambda _store: None)
    monkeypatch.setattr("core.config_commands.load_profile_api_key", lambda _profile_id: "key")

    assert handle_config_command("", store, settings, console, object()) is None
    assert store.profiles == {"stable-id": edited}
    assert received == [(old, {"profile_id": "stable-id"})]
    assert settings.model == "gpt-new"


def test_config_create_uses_collision_safe_profile_id(tmp_path, monkeypatch):
    existing = make_profile(tmp_path, "Work")
    created = make_profile(tmp_path, "Work", model="gpt-new")
    store = ProfileStore(active_profile="work", profiles={"work": existing})
    settings = SessionSettings()
    console = ConfigConsole(["Создать профиль"])
    received = []
    monkeypatch.setattr(
        "core.config_commands.create_profile_interactively",
        lambda _console, **kwargs: received.append(kwargs) or created,
    )
    monkeypatch.setattr("core.config_commands.save_profile_store", lambda _store: None)
    monkeypatch.setattr("core.config_commands.load_profile_api_key", lambda _profile_id: "key")

    handle_config_command("", store, settings, console, object())

    assert store.active_profile == "work-2"
    assert store.profiles["work-2"] is created
    assert list(received[0]["existing_profile_ids"]) == ["work"]


def test_cancel_keeps_client_and_profile_unchanged(tmp_path):
    active = make_profile(tmp_path, "Work")
    store = ProfileStore(active_profile="work", profiles={"work": active})
    settings = SessionSettings(provider="openai", model="gpt-5.6")
    client = object()

    returned = handle_config_command("", store, settings, ConfigConsole(["Отмена"]), client)

    assert returned is client
    assert store.active_profile == "work"


def test_failed_profile_switch_rolls_back_store_settings_and_client(tmp_path, monkeypatch):
    first = make_profile(tmp_path, "First")
    second = make_profile(tmp_path, "Second", provider="nvidia", model="nvidia-model")
    store = ProfileStore(active_profile="first", profiles={"first": first, "second": second})
    settings = SessionSettings(provider="openai", model="gpt-5.6", api_key="old-key")
    client = object()
    monkeypatch.setattr(
        "core.config_commands.save_profile_store",
        lambda _store: (_ for _ in ()).throw(OSError("disk full")),
    )

    returned = handle_config_command("second", store, settings, ConfigConsole(), client)

    assert returned is client
    assert store.active_profile == "first"
    assert store.profiles == {"first": first, "second": second}
    assert (settings.provider, settings.model, settings.api_key) == (
        "openai",
        "gpt-5.6",
        "old-key",
    )


def test_failed_profile_edit_restores_previous_key(tmp_path, monkeypatch):
    old = make_profile(tmp_path, "Old", provider="openai")
    edited = make_profile(tmp_path, "Old", provider="nvidia", model="nvidia-model")
    store = ProfileStore(active_profile="stable", profiles={"stable": old})
    settings = SessionSettings(provider="openai", model="gpt-5.6", api_key="old-key")
    label = "Old · openai · gpt-5.6 [stable]"
    restored = []
    monkeypatch.setattr(
        "core.config_commands.create_profile_interactively",
        lambda *_args, **_kwargs: edited,
    )
    monkeypatch.setattr("core.config_commands.load_profile_api_key", lambda _profile_id: "old-key")
    monkeypatch.setattr(
        "core.config_commands.save_profile_store",
        lambda _store: (_ for _ in ()).throw(OSError("disk full")),
    )
    monkeypatch.setattr(
        "core.config_commands.save_profile_api_key",
        lambda *args: restored.append(args),
    )

    returned = handle_config_command(
        "",
        store,
        settings,
        ConfigConsole(["Изменить профиль", label]),
        object(),
    )

    assert returned is not None
    assert store.profiles["stable"] is old
    assert restored == [("stable", "openai", "old-key")]
