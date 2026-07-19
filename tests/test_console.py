import io

from rich.console import Console as RichConsole

from core.console import Console


def test_header_contains_session_details(monkeypatch):
    monkeypatch.setattr("sys.stdin.isatty", lambda: False)
    monkeypatch.setattr("sys.stdout.isatty", lambda: False)
    stream = io.StringIO()
    console = Console()
    console.output = RichConsole(file=stream, force_terminal=False, width=100)

    console.header("nvidia", "test-model", "C:/project", agent=True)

    rendered = stream.getvalue()
    assert "CITADEX" in rendered
    assert "test-model" in rendered
    assert "AGENT" in rendered
    assert "C:/project" in rendered


def test_regular_prompt_disables_password_mode_after_secret(monkeypatch):
    class RecordingSession:
        def __init__(self):
            self.password_modes: list[bool | None] = []

        def prompt(self, _message, **kwargs):
            self.password_modes.append(kwargs.get("is_password"))
            return "value"

    monkeypatch.setattr("sys.stdin.isatty", lambda: False)
    monkeypatch.setattr("sys.stdout.isatty", lambda: False)
    console = Console()
    session = RecordingSession()
    console.session = session  # type: ignore[assignment]

    console.secret("API key")
    console.prompt()

    assert session.password_modes == [True, False]
