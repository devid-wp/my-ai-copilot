import io

from rich.console import Console as RichConsole

from core.console import Console


def test_header_contains_pet_and_session_details(monkeypatch):
    monkeypatch.setattr("sys.stdin.isatty", lambda: False)
    monkeypatch.setattr("sys.stdout.isatty", lambda: False)
    stream = io.StringIO()
    console = Console()
    console.output = RichConsole(file=stream, force_terminal=False, width=100)

    console.header("nvidia", "test-model", "C:/project", agent=True)

    rendered = stream.getvalue()
    assert "люми" in rendered
    assert "(•ᴗ•)" in rendered
    assert ".-^-." not in rendered
    assert "test-model" in rendered
    assert "AGENT" in rendered
    assert "C:/project" in rendered
