from core.preferences import UserPreferences, load_preferences, save_preferences


def test_preferences_round_trip(tmp_path):
    target = tmp_path / "config.json"
    preferences = UserPreferences(
        provider="ollama",
        mode="agent",
        permissions="auto",
        models={"ollama": "qwen2.5:3b"},
    )

    save_preferences(preferences, target)

    assert load_preferences(target) == preferences


def test_invalid_preferences_fall_back_to_safe_defaults(tmp_path):
    target = tmp_path / "config.json"
    target.write_text('{"provider":"unknown","mode":"auto"}', encoding="utf-8")

    preferences = load_preferences(target)

    assert preferences.provider == "nvidia"
    assert preferences.mode == "chat"
    assert preferences.permissions == "ask"


def test_preferences_remember_recent_projects(tmp_path):
    preferences = UserPreferences()
    preferences.remember_project(str(tmp_path / "one"))
    preferences.remember_project(str(tmp_path / "two"))
    preferences.remember_project(str(tmp_path / "one"))
    assert preferences.project_root.endswith("one")
    assert len(preferences.recent_projects) == 2
