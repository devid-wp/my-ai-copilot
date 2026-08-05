from collections import defaultdict

from core.config_profiles import ConfigProfile
from core.config_wizard import create_profile_interactively


class WizardConsole:
    def __init__(self, *, inputs=None, choices=None, secrets=None):
        self.inputs = defaultdict(list, inputs or {})
        self.choices = defaultdict(list, choices or {})
        self.secrets = list(secrets or [])
        self.defaults = []
        self.messages = []

    def input(self, label):
        return self.inputs[label].pop(0)

    def choose(self, title, _options, default=None):
        self.defaults.append((title, default))
        return self.choices[title].pop(0)

    def secret(self, _label):
        return self.secrets.pop(0)

    def __getattr__(self, name):
        def record(message, *_args):
            self.messages.append((name, message))

        return record


def test_cloud_wizard_verifies_then_saves_profile_key(tmp_path, monkeypatch):
    events = []
    monkeypatch.setattr(
        "core.config_wizard.probe_provider_key",
        lambda provider, key: events.append(("key", provider, key)),
    )
    monkeypatch.setattr(
        "core.config_wizard.validate_provider_model_access",
        lambda provider, model, key: events.append(("model", provider, model, key)),
    )
    monkeypatch.setattr(
        "core.config_wizard.save_profile_api_key",
        lambda profile_id, provider, key: events.append(("saved", profile_id, provider, key)),
    )
    console = WizardConsole(
        inputs={
            "Название профиля": ["NVIDIA Fast"],
            "Имя модели": ["z-ai/glm-5.2"],
            "Рабочая папка": [str(tmp_path)],
        },
        choices={
            "Провайдер": ["nvidia"],
            "Режим": ["chat"],
        },
        secrets=["nvapi-secret"],
    )

    result = create_profile_interactively(console)

    assert result == ConfigProfile(
        name="NVIDIA Fast",
        provider="nvidia",
        model="z-ai/glm-5.2",
        mode="chat",
        permissions="ask",
        project_root=str(tmp_path),
    )
    assert events == [
        ("key", "nvidia", "nvapi-secret"),
        ("model", "nvidia", "z-ai/glm-5.2", "nvapi-secret"),
        ("saved", "nvidia-fast", "nvidia", "nvapi-secret"),
    ]


def test_model_is_checked_only_for_explicitly_selected_provider(tmp_path, monkeypatch):
    checked = []
    monkeypatch.setattr("core.config_wizard.probe_provider_key", lambda *_args: None)
    monkeypatch.setattr(
        "core.config_wizard.validate_provider_model_access",
        lambda provider, model, _key: checked.append((provider, model)),
    )
    monkeypatch.setattr("core.config_wizard.save_profile_api_key", lambda *_args: None)
    console = WizardConsole(
        inputs={
            "ÐÐ°Ð·Ð²Ð°Ð½Ð¸Ðµ Ð¿ÑÐ¾ÑÐ¸Ð»Ñ": ["Explicit OpenAI"],
            "ÐÐ¼Ñ Ð¼Ð¾Ð´ÐµÐ»Ð¸": ["nvidia/looking-model"],
            "Ð Ð°Ð±Ð¾ÑÐ°Ñ Ð¿Ð°Ð¿ÐºÐ°": [str(tmp_path)],
        },
        choices={
            "ÐÑÐ¾Ð²Ð°Ð¹Ð´ÐµÑ": ["openai"],
            "Ð ÐµÐ¶Ð¸Ð¼": ["chat"],
        },
        secrets=["openai-secret"],
    )

    console.inputs[
        "\u041d\u0430\u0437\u0432\u0430\u043d\u0438\u0435 \u043f\u0440\u043e\u0444\u0438\u043b\u044f"
    ] = ["Explicit OpenAI"]
    console.inputs["\u0418\u043c\u044f \u043c\u043e\u0434\u0435\u043b\u0438"] = ["nvidia/looking-model"]
    console.inputs[
        "\u0420\u0430\u0431\u043e\u0447\u0430\u044f \u043f\u0430\u043f\u043a\u0430"
    ] = [str(tmp_path)]
    console.choices["\u041f\u0440\u043e\u0432\u0430\u0439\u0434\u0435\u0440"] = ["openai"]
    console.choices["\u0420\u0435\u0436\u0438\u043c"] = ["chat"]

    result = create_profile_interactively(console)

    assert result.provider == "openai"
    assert checked == [("openai", "nvidia/looking-model")]


def test_wizard_retries_without_saving_after_validation_error(tmp_path, monkeypatch):
    checks = []
    saved = []
    monkeypatch.setattr("core.config_wizard.probe_provider_key", lambda *_args: None)

    def validate(provider, model, _key):
        checks.append((provider, model))
        if model == "removed-model":
            raise ValueError("model unavailable")

    monkeypatch.setattr("core.config_wizard.validate_provider_model_access", validate)
    monkeypatch.setattr("core.config_wizard.save_profile_api_key", lambda *args: saved.append(args))
    console = WizardConsole(
        inputs={
            "Название профиля": ["NVIDIA", "NVIDIA"],
            "Имя модели": ["removed-model", "valid-model"],
            "Рабочая папка": [str(tmp_path), str(tmp_path)],
        },
        choices={
            "Провайдер": ["nvidia", "nvidia"],
            "Режим": ["chat", "chat"],
        },
        secrets=["nvapi-secret", "nvapi-secret"],
    )

    result = create_profile_interactively(console)

    assert result.model == "valid-model"
    assert checks == [("nvidia", "removed-model"), ("nvidia", "valid-model")]
    assert len(saved) == 1
    assert any(level == "error" and "model unavailable" in message for level, message in console.messages)


def test_local_wizard_never_reads_or_saves_api_key(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "core.config_wizard.save_profile_api_key",
        lambda *_args: (_ for _ in ()).throw(AssertionError("must not save a local key")),
    )
    console = WizardConsole(
        inputs={
            "Название профиля": ["Local"],
            "Имя модели": ["qwen-local"],
            "Рабочая папка": [str(tmp_path)],
        },
        choices={
            "Провайдер": ["local"],
            "Режим": ["agent"],
            "Разрешения": ["auto"],
        },
    )

    result = create_profile_interactively(console)

    assert result.provider == "local"
    assert result.permissions == "auto"


def test_editing_profile_reuses_stable_id_and_saved_key(tmp_path, monkeypatch):
    existing = ConfigProfile(
        name="Old name",
        provider="openai",
        model="gpt-5-nano",
        mode="chat",
        permissions="ask",
        project_root=str(tmp_path),
    )
    saved = []
    monkeypatch.setattr("core.config_wizard.load_profile_api_key", lambda profile_id: "saved-key")
    monkeypatch.setattr("core.config_wizard.probe_provider_key", lambda *_args: None)
    monkeypatch.setattr("core.config_wizard.validate_provider_model_access", lambda *_args: None)
    monkeypatch.setattr(
        "core.config_wizard.save_profile_api_key",
        lambda profile_id, provider, key: saved.append((profile_id, provider, key)),
    )
    console = WizardConsole(
        inputs={
            "Название профиля (Enter = Old name)": ["New name"],
            "Имя модели (Enter = gpt-5-nano)": [""],
            f"Рабочая папка (Enter = {tmp_path})": [""],
        },
        choices={"Провайдер": ["openai"], "Режим": ["chat"]},
        secrets=[""],
    )

    result = create_profile_interactively(console, existing, profile_id="openai-agent")

    assert result.name == "New name"
    assert result.model == "gpt-5-nano"
    assert saved == [("openai-agent", "openai", "saved-key")]
