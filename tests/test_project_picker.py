from core.preferences import UserPreferences
from main import choose_recent_project


class PickerConsole:
    def __init__(self):
        self.options = []

    def choose(self, _title, options, default=None):
        self.options = options
        return default

    def input(self, _label):
        return ""


def test_picker_offers_recent_projects(tmp_path):
    recent = tmp_path / "recent"
    recent.mkdir()
    console = PickerConsole()
    selected = choose_recent_project(console, UserPreferences(recent_projects=[str(recent)]), str(tmp_path))
    assert selected == str(tmp_path.resolve())
    assert any("recent" in option for option in console.options)


def test_picker_defaults_to_current_directory_even_when_it_was_recent(tmp_path):
    old = tmp_path / "old"
    current = tmp_path / "current"
    old.mkdir()
    current.mkdir()
    console = PickerConsole()

    selected = choose_recent_project(
        console,
        UserPreferences(recent_projects=[str(old), str(current)]),
        str(current),
    )

    assert selected == str(current)
    assert console.options[0].endswith(str(current))
