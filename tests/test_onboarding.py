from core.preferences import UserPreferences
from main import SessionSettings, run_startup_setup


class WizardConsole:
    def __init__(self, answers, secret=""):
        self.answers = answers
        self.secret_value = secret
        self.secret_calls = 0
        self.defaults = {}
        self.messages = []

    def choose(self, title, _options, default=None):
        self.defaults[title] = default
        return self.answers[title]

    def secret(self, _label):
        self.secret_calls += 1
        return self.secret_value

    def input(self, _label):
        return self.answers["Модель"]

    def __getattr__(self, name):
        def record(message, *_args):
            self.messages.append((name, message))

        return record


def test_first_run_collects_and_saves_cloud_key(monkeypatch):
    saved_keys = []
    saved_preferences = []
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr("main.save_api_key", lambda provider, key: saved_keys.append((provider, key)))
    monkeypatch.setattr("main.save_preferences", saved_preferences.append)
    console = WizardConsole(
        {
            "Режим запуска": "chat",
            "Провайдер": "openai",
            "Модель": "gpt-5.6",
        },
        secret="openai-secret",
    )
    settings = SessionSettings()

    assert run_startup_setup(settings, console, UserPreferences()) is True

    assert saved_keys == [("openai", "openai-secret")]
    assert console.secret_calls == 1
    assert settings.provider == "openai"
    assert settings.model == "gpt-5.6"
    assert settings.mode == "chat"
    assert saved_preferences[0].models["openai"] == "gpt-5.6"


def test_repeat_run_reuses_key_and_offers_saved_defaults(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "already-saved")
    monkeypatch.setattr("main.save_preferences", lambda _preferences: None)
    preferences = UserPreferences(
        provider="openai",
        mode="chat",
        models={"openai": "gpt-5.6"},
    )
    console = WizardConsole(
        {
            "Режим запуска": "chat",
            "Провайдер": "openai",
            "Модель": "gpt-5.6",
        }
    )
    settings = SessionSettings(provider="openai", model="gpt-5.6")

    assert run_startup_setup(settings, console, preferences) is True

    assert console.secret_calls == 0
    assert console.defaults["Режим запуска"] == "chat"
    assert console.defaults["Провайдер"] == "openai"


def test_switching_provider_does_not_reuse_previous_provider_model(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "openai-key")
    monkeypatch.setattr("main.save_preferences", lambda _preferences: None)
    preferences = UserPreferences(
        provider="nvidia",
        mode="chat",
        models={"nvidia": "z-ai/glm-5.2", "openai": "gpt-5-nano"},
    )
    console = WizardConsole(
        {
            "Режим запуска": "chat",
            "Провайдер": "openai",
            "Модель": "",
        }
    )
    settings = SessionSettings(provider="nvidia", model="z-ai/glm-5.2")

    assert run_startup_setup(settings, console, preferences) is True

    assert settings.provider == "openai"
    assert settings.model == "gpt-5-nano"


def test_agent_setup_reprompts_after_incompatible_ollama_model(monkeypatch):
    compatibility = iter([False, True])
    chosen_models = iter(["weak-model", "good-model"])
    monkeypatch.setattr("main.provider_models", lambda _provider: ["weak-model", "good-model"])
    monkeypatch.setattr(
        "main.verify_tool_compatibility",
        lambda _settings, _console: next(compatibility),
    )
    monkeypatch.setattr("main.save_preferences", lambda _preferences: None)
    console = WizardConsole(
        {
            "Режим запуска": "agent",
            "Разрешения агента": "Спрашивать перед действиями",
            "Провайдер": "ollama",
            "Модель": "unused",
        }
    )

    def choose(title, _options, default=None):
        if title == "Модель":
            return next(chosen_models)
        return console.answers[title]

    console.choose = choose
    settings = SessionSettings(provider="ollama")

    assert run_startup_setup(settings, console, UserPreferences(provider="ollama")) is True
    assert settings.model == "good-model"
    assert settings.agent is True


def test_agent_setup_remembers_automatic_permissions(monkeypatch):
    from core.tool_compatibility import ToolCompatibility

    monkeypatch.setenv("NVIDIA_API_KEY", "nvapi-saved")
    monkeypatch.setattr("main.validate_provider_model_access", lambda *_args: None)
    monkeypatch.setattr("main.provider_models", lambda _provider: ["meta/llama-3.1-8b-instruct"])
    monkeypatch.setattr(
        "main.probe_cloud_tool_support",
        lambda *_args: ToolCompatibility.SUPPORTED,
    )
    saved_preferences = []
    monkeypatch.setattr("main.save_preferences", saved_preferences.append)
    console = WizardConsole(
        {
            "Режим запуска": "agent",
            "Разрешения агента": "Автоподтверждение (полный доступ к рабочей папке)",
            "Провайдер": "nvidia",
            "Модель": "meta/llama-3.1-8b-instruct",
        }
    )
    settings = SessionSettings()

    assert run_startup_setup(settings, console, UserPreferences()) is True

    assert settings.auto_approve is True
    assert saved_preferences[0].permissions == "auto"
