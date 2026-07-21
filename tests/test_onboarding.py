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

    def __getattr__(self, name):
        def record(message, *_args):
            self.messages.append((name, message))

        return record


def test_first_run_collects_and_saves_cloud_key(monkeypatch):
    saved_keys = []
    saved_preferences = []
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setattr("main.save_api_key", lambda provider, key: saved_keys.append((provider, key)))
    monkeypatch.setattr("main.save_preferences", saved_preferences.append)
    console = WizardConsole(
        {
            "Режим запуска": "chat",
            "Провайдер": "gemini",
            "Модель": "gemini-2.0-flash",
        },
        secret="gemini-secret",
    )
    settings = SessionSettings()

    assert run_startup_setup(settings, console, UserPreferences()) is True

    assert saved_keys == [("gemini", "gemini-secret")]
    assert console.secret_calls == 1
    assert settings.provider == "gemini"
    assert settings.model == "gemini-2.0-flash"
    assert settings.mode == "chat"
    assert saved_preferences[0].models["gemini"] == "gemini-2.0-flash"


def test_repeat_run_reuses_key_and_offers_saved_defaults(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "already-saved")
    monkeypatch.setattr("main.save_preferences", lambda _preferences: None)
    preferences = UserPreferences(
        provider="gemini",
        mode="chat",
        models={"gemini": "gemini-2.5-pro"},
    )
    console = WizardConsole(
        {
            "Режим запуска": "chat",
            "Провайдер": "gemini",
            "Модель": "gemini-2.5-pro",
        }
    )
    settings = SessionSettings(provider="gemini", model="gemini-2.5-pro")

    assert run_startup_setup(settings, console, preferences) is True

    assert console.secret_calls == 0
    assert console.defaults["Режим запуска"] == "chat"
    assert console.defaults["Провайдер"] == "gemini"
    assert console.defaults["Модель"] == "gemini-2.5-pro"


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
