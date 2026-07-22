import io

from rich.console import Console as RichConsole

from core.agent_loop import ToolRunRecord
from core.console import Console
from core.diagnostics import SessionDiagnostics
from core.tools import ToolStatus


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


def test_choose_accepts_default_on_empty_input(monkeypatch):
    monkeypatch.setattr("sys.stdin.isatty", lambda: False)
    monkeypatch.setattr("sys.stdout.isatty", lambda: False)
    monkeypatch.setattr("builtins.input", lambda _prompt: "")
    console = Console()

    assert console.choose("Mode", ["agent", "chat"], default="chat") == "chat"


def test_tool_call_rendering_is_compact_and_hides_file_content(monkeypatch):
    monkeypatch.setattr("sys.stdin.isatty", lambda: False)
    monkeypatch.setattr("sys.stdout.isatty", lambda: False)
    stream = io.StringIO()
    console = Console()
    console.output = RichConsole(file=stream, force_terminal=False, width=120)

    console.tool(
        "create_file",
        {"path": "src/example.py", "content": "super secret content"},
    )
    console.tool_result({"status": "created", "path": "C:/project/src/example.py", "bytes": 20})

    rendered = stream.getvalue()
    assert "WRITE" in rendered
    assert "create_file" in rendered
    assert "src/example.py" in rendered
    assert "20 B" in rendered
    assert "super secret content" not in rendered


def test_tool_error_rendering_includes_structured_code(monkeypatch):
    monkeypatch.setattr("sys.stdin.isatty", lambda: False)
    monkeypatch.setattr("sys.stdout.isatty", lambda: False)
    stream = io.StringIO()
    console = Console()
    console.output = RichConsole(file=stream, force_terminal=False, width=120)

    console.tool_result(
        {
            "status": "error",
            "code": "INVALID_ARGUMENTS",
            "error": "'path' is required",
        }
    )

    rendered = stream.getvalue()
    assert "INVALID_ARGUMENTS" in rendered
    assert "'path' is required" in rendered


def test_agent_summary_lists_actions(monkeypatch):
    monkeypatch.setattr("sys.stdin.isatty", lambda: False)
    monkeypatch.setattr("sys.stdout.isatty", lambda: False)
    stream = io.StringIO()
    console = Console()
    console.output = RichConsole(file=stream, force_terminal=False, width=120)

    console.agent_summary([ToolRunRecord("create_file", ToolStatus.SUCCESS, "page.html")])

    rendered = stream.getvalue()
    assert "Готово" in rendered
    assert "create_file" in rendered
    assert "page.html" in rendered


def test_status_renders_provider_health_and_session_details(monkeypatch):
    monkeypatch.setattr("sys.stdin.isatty", lambda: False)
    monkeypatch.setattr("sys.stdout.isatty", lambda: False)
    stream = io.StringIO()
    console = Console()
    console.output = RichConsole(file=stream, force_terminal=False, width=120)

    console.status(
        SessionDiagnostics(
            provider="ollama",
            provider_state="online",
            model="qwen2.5:3b",
            model_state="available",
            tools_state="supported",
            mode="agent",
            permissions="ask",
            project_root="C:/project",
            message_count=7,
            client_state="initialized",
        )
    )

    rendered = stream.getvalue()
    assert "online" in rendered
    assert "qwen2.5:3b" in rendered
    assert "supported" in rendered
    assert "C:/project" in rendered
    assert "7" in rendered
