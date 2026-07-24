"""Rich terminal interface for Citadex."""

from __future__ import annotations

import os
import sys
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.styles import Style
from rich import box
from rich.console import Console as RichConsole
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from core.agent_loop import ToolRunRecord
from core.diagnostics import SessionDiagnostics
from core.tools import ToolStatus

PURPLE = "#a78bfa"
PURPLE_DARK = "#7c3aed"
CYAN = "#22d3ee"
GREEN = "#4ade80"
YELLOW = "#facc15"
RED = "#fb7185"
MUTED = "#71717a"
SURFACE = "#18181b"

TOOL_ACTIONS = {
    "create_file": "WRITE",
    "write_file": "WRITE",
    "edit_file": "EDIT",
    "delete_file": "DELETE",
    "make_directory": "MKDIR",
    "execute_cmd": "RUN",
    "list_directory": "LIST",
    "read_file": "READ",
    "search_in_files": "SEARCH",
    "move_file": "MOVE",
    "copy_file": "COPY",
    "file_exists": "EXISTS",
    "get_file_info": "INFO",
    "git_status": "GIT",
    "git_diff": "DIFF",
    "run_tests": "TEST",
    "format_code": "FORMAT",
}

SLASH_COMMANDS = [
    "/provider",
    "/model",
    "/mode",
    "/project",
    "/keys",
    "/undo",
    "/permissions",
    "/status",
    "/doctor",
    "/clear",
    "/help",
    "/exit",
]
LOCAL_SLASH_COMMANDS = [
    "/mode",
    "/project",
    "/undo",
    "/permissions",
    "/status",
    "/doctor",
    "/clear",
    "/help",
    "/exit",
]


class Console:
    def __init__(self, *, local_only: bool = False) -> None:
        self.local_only = local_only
        self.output = RichConsole(highlight=False, soft_wrap=True)
        self.session: PromptSession[str] | None = None
        if sys.stdin.isatty() and sys.stdout.isatty():
            self.session = PromptSession(
                multiline=False,
                completer=WordCompleter(
                    LOCAL_SLASH_COMMANDS if local_only else SLASH_COMMANDS,
                    sentence=True,
                ),
                complete_while_typing=True,
                style=Style.from_dict(
                    {
                        "brand": "bold #a78bfa",
                        "prompt": "bold #22d3ee",
                        "completion-menu": "bg:#18181b #d4d4d8",
                        "completion-menu.completion.current": "bg:#7c3aed #ffffff bold",
                    }
                ),
            )

    def header(self, provider: str, model: str, project: str, agent: bool) -> None:
        mode = "AGENT" if agent else "CHAT"
        mode_color = PURPLE if agent else CYAN
        details = Table.grid(expand=True, padding=(0, 1))
        details.add_column(width=2)
        details.add_column(ratio=1)
        details.add_column(justify="right")
        details.add_row(
            Text("●", style=CYAN),
            Text.assemble(
                (provider.upper(), "bold white"),
                ("  /  ", MUTED),
                (model, "white"),
            ),
            Text(f" {mode} ", style=f"bold {mode_color} on {SURFACE}"),
        )
        details.add_row(Text("⌁", style=MUTED), Text(project, style=MUTED), Text("ready", style=GREEN))
        title = Text.assemble(
            (" CITADEX ", "bold white on #7c3aed"),
            (" terminal coding agent ", MUTED),
        )
        self.output.print()
        self.output.print(
            Panel(
                details,
                title=title,
                title_align="left",
                border_style=PURPLE_DARK,
                box=box.ROUNDED,
                padding=(1, 1),
            )
        )

    def quick_start(self, diagnostics: SessionDiagnostics) -> bool:
        details = Table.grid(expand=True, padding=(0, 1))
        details.add_column(style=MUTED, width=13)
        details.add_column(style="bold white")
        details.add_row("PROJECT", Path(diagnostics.project_root).name)
        details.add_row("PROVIDER", diagnostics.provider.upper())
        details.add_row("MODEL", diagnostics.model)
        details.add_row(
            "MODE",
            Text(diagnostics.mode.upper(), style=PURPLE if diagnostics.mode == "agent" else CYAN),
        )
        details.add_row("PERMISSIONS", diagnostics.permissions)
        details.add_row("", "")
        details.add_row("ENTER", "продолжить")
        details.add_row("C", "изменить настройки")
        title = Text.assemble(
            (" CITADEX ", "bold white on #7c3aed"),
            (" ready ", MUTED),
        )
        self.output.print(
            Panel(
                details,
                title=title,
                title_align="left",
                border_style=PURPLE_DARK,
                box=box.ROUNDED,
                padding=(1, 1),
            )
        )
        return self.input("Запуск").strip().casefold() != "c"

    def prompt(self) -> str:
        return self._read("citadex ❯ ", HTML("<brand>citadex</brand> <prompt>❯</prompt> "))

    def secret(self, label: str) -> str:
        """Read a secret without echoing it to the terminal."""
        plain_prompt = f"{label} ❯ "
        if self.session is None:
            from getpass import getpass

            return getpass(plain_prompt)
        return self.session.prompt(
            HTML(f"<brand>{label}</brand> <prompt>❯</prompt> "),
            is_password=True,
        )

    def input(self, label: str) -> str:
        return self._read(f"{label} ❯ ", HTML(f"<brand>{label}</brand> <prompt>❯</prompt> "))

    def choose(self, title: str, options: list[str], default: str | None = None) -> str:
        if default not in options:
            default = None
        menu = Table(box=box.SIMPLE, show_header=False, padding=(0, 1), border_style=MUTED)
        menu.add_column("number", justify="right", style=f"bold {PURPLE}", width=3)
        menu.add_column("option", style="white")
        for index, option in enumerate(options, 1):
            label = f"{option}  [default]" if option == default else option
            menu.add_row(str(index), label)
        self.output.print(Panel(menu, title=f"[bold]{title}[/bold]", border_style=PURPLE, box=box.ROUNDED))
        while True:
            answer = self._read("select ❯ ", HTML("<brand>select</brand> <prompt>❯</prompt> ")).strip()
            if not answer and default is not None:
                return default
            if answer in options:
                return answer
            if answer.isdigit() and 1 <= int(answer) <= len(options):
                return options[int(answer) - 1]
            self.error("Введите номер или название из списка")

    def hint(self, _message: str) -> None:
        hint = Text()
        commands = LOCAL_SLASH_COMMANDS[:5] if self.local_only else SLASH_COMMANDS[:5]
        for index, command in enumerate(commands):
            if index:
                hint.append("  ·  ", style=MUTED)
            hint.append(command, style=PURPLE)
        hint.append("    TAB to complete", style=f"italic {MUTED}")
        self.output.print(hint)
        self.output.print()

    def status(self, diagnostics: SessionDiagnostics) -> None:
        table = Table.grid(padding=(0, 2))
        table.add_column(style=MUTED)
        table.add_column(style="bold white")
        table.add_row(
            "provider",
            Text.assemble(
                (diagnostics.provider, "bold white"),
                ("  ·  ", MUTED),
                (diagnostics.provider_state, self._state_color(diagnostics.provider_state)),
            ),
        )
        table.add_row(
            "model",
            Text.assemble(
                (diagnostics.model, "bold white"),
                ("  ·  ", MUTED),
                (diagnostics.model_state, self._state_color(diagnostics.model_state)),
            ),
        )
        table.add_row(
            "tools",
            Text(diagnostics.tools_state, style=self._state_color(diagnostics.tools_state)),
        )
        table.add_row(
            "mode",
            Text(diagnostics.mode, style=PURPLE if diagnostics.mode == "agent" else CYAN),
        )
        table.add_row(
            "permissions",
            Text(
                diagnostics.permissions,
                style=YELLOW if diagnostics.permissions == "auto" else GREEN,
            ),
        )
        table.add_row("project", diagnostics.project_root)
        table.add_row("messages", str(diagnostics.message_count))
        table.add_row(
            "ollama", Text(diagnostics.ollama_state, style=self._state_color(diagnostics.ollama_state))
        )
        table.add_row("client", diagnostics.client_state)
        self.output.print(Panel(table, title="[bold]Session[/bold]", border_style=MUTED, box=box.ROUNDED))

    @staticmethod
    def _state_color(state: str) -> str:
        if state in {"online", "available", "supported", "configured", "initialized"}:
            return GREEN
        if state in {"unknown", "not checked", "not started"}:
            return YELLOW
        return RED

    def stream(self, tokens: Iterable[str]) -> str:
        parts: list[str] = []
        self.output.print(Text("CITADEX", style=f"bold {PURPLE}"), end=" ")
        for token in tokens:
            parts.append(token)
            self.output.print(token, end="", markup=False, highlight=False)
        self.output.print("\n")
        return "".join(parts)

    def response(self, content: str) -> None:
        """Render a completed response after agent tool-call detection."""
        self.output.print(Text("CITADEX", style=f"bold {PURPLE}"), end=" ")
        self.output.print(content, markup=False, highlight=False)
        self.output.print()

    def activity(self, message: str) -> None:
        self.output.print(Text.assemble(("◇ ", CYAN), (message, MUTED)))

    def agent_summary(self, records: list[ToolRunRecord], project_root: str = "") -> None:
        if not records:
            return
        table = Table.grid(padding=(0, 1))
        table.add_column(width=2)
        table.add_column(style="bold white")
        table.add_column(style=MUTED)
        for record in records[-12:]:
            successful = record.status is ToolStatus.SUCCESS
            symbol = Text("✓" if successful else "✕", style=GREEN if successful else RED)
            table.add_row(symbol, record.name, self._shorten(record.detail))
        if len(records) > 12:
            table.add_row(Text("…", style=MUTED), f"{len(records) - 12} earlier action(s)", "")
        self.output.print(
            Panel(table, title="[bold]Agent summary[/bold]", border_style=MUTED, box=box.ROUNDED)
        )
        changed = next(
            (
                record.detail
                for record in reversed(records)
                if record.name in {"create_file", "edit_file"} and record.detail
            ),
            "",
        )
        if changed:
            path = changed if os.path.isabs(changed) else os.path.abspath(os.path.join(project_root, changed))
            self.output.print(Text.assemble(("Путь: ", MUTED), (path, "bold white")))

    def tool(self, name: str, arguments: dict[str, Any]) -> None:
        action = TOOL_ACTIONS.get(name, "TOOL")
        detail = self._tool_detail(name, arguments)
        line = Text.assemble(
            ("◆ ", CYAN),
            (action, f"bold {CYAN}"),
            ("  ", MUTED),
            (name, "bold white"),
        )
        if detail:
            line.append("  ·  ", style=MUTED)
            line.append(detail, style=MUTED)
        self.output.print(line)

    def tool_result(self, result: dict[str, Any]) -> None:
        if result.get("status") == "error" or "error" in result:
            self.output.print(
                Text.assemble(
                    ("  ✕ ", RED),
                    (str(result.get("code", "ERROR")), f"bold {RED}"),
                    ("  ·  ", MUTED),
                    (self._shorten(result.get("error", "unknown error")), MUTED),
                )
            )
            return

        status = str(result.get("status", "completed")).upper()
        details = self._result_details(result)
        color = YELLOW if result.get("returncode") not in {None, 0} else GREEN
        line = Text.assemble(("  ✓ ", color), (status, f"bold {color}"))
        if details:
            line.append("  ·  ", style=MUTED)
            line.append("  ·  ".join(details), style=MUTED)
        self.output.print(line)

    @classmethod
    def _tool_detail(cls, name: str, arguments: dict[str, Any]) -> str:
        path = cls._shorten(arguments.get("path", ""))
        if name == "execute_cmd":
            return cls._shorten(arguments.get("command", ""))
        if name == "search_in_files":
            pattern = cls._shorten(arguments.get("pattern", ""), 60)
            return f'"{pattern}" in {path or "."}'
        if name == "create_file":
            size = len(str(arguments.get("content", "")).encode("utf-8"))
            return f"{path}  ·  {size} B"
        if name == "edit_file":
            patches = len(arguments.get("patches") or [])
            return f"{path}  ·  {patches} patch(es)"
        return path

    @classmethod
    def _result_details(cls, result: dict[str, Any]) -> list[str]:
        details: list[str] = []
        if result.get("path"):
            details.append(cls._shorten(result["path"]))
        if "bytes" in result:
            details.append(f"{result['bytes']} B")
        if "patches" in result:
            details.append(f"{result['patches']} patch(es)")
        if "count" in result:
            details.append(f"{result['count']} match(es)")
        if isinstance(result.get("entries"), list):
            details.append(f"{len(result['entries'])} item(s)")
        if "returncode" in result:
            details.append(f"exit {result['returncode']}")
        if result.get("truncated"):
            details.append("truncated")
        return details

    @staticmethod
    def _shorten(value: Any, limit: int = 100) -> str:
        text = str(value).replace("\r", "").replace("\n", " ↵ ")
        return text if len(text) <= limit else f"{text[: limit - 1]}…"

    def confirm(self, action: str, detail: str) -> bool:
        body = Text.assemble((action, "bold white"), ("\n"), (detail, MUTED))
        self.output.print(
            Panel(
                body,
                title=f"[bold {YELLOW}]Permission required[/bold {YELLOW}]",
                border_style=YELLOW,
            )
        )
        answer = self._read("allow? [y/N] ", HTML("<brand>allow?</brand> <prompt>[y/N]</prompt> "))
        return answer.strip().lower() in {"y", "yes", "д", "да"}

    def _read(self, plain_prompt: str, rich_prompt: HTML) -> str:
        if self.session is None:
            return input(plain_prompt)
        # PromptSession keeps per-call options for later prompts. Explicitly
        # disable password mode after secret input so regular chat stays visible.
        return self.session.prompt(rich_prompt, is_password=False)

    def success(self, message: str) -> None:
        self.output.print(
            Panel(
                Text(message, style=GREEN),
                border_style=GREEN,
                box=box.ROUNDED,
            )
        )

    def warning(self, message: str) -> None:
        self.output.print(Panel(Text(message, style=YELLOW), border_style=YELLOW, box=box.ROUNDED))

    def error(self, message: str) -> None:
        self.output.print(
            Panel(
                Text(message, style=RED),
                title="[bold]Error[/bold]",
                border_style=RED,
                box=box.ROUNDED,
            )
        )

    def help(self) -> None:
        commands = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
        commands.add_column(style=f"bold {PURPLE}", no_wrap=True)
        commands.add_column(style="white")
        rows = [
            ("/project <path>", "сменить рабочую папку"),
            ("/undo", "отменить последнее изменение файла"),
            ("/mode [chat|agent]", "переключить режим работы"),
            ("/permissions [ask|auto]", "настроить подтверждения действий"),
            ("/status", "показать настройки сессии"),
            ("/doctor", "проверить окружение, провайдера и модель"),
            ("/clear", "очистить историю"),
            ("/exit", "выйти"),
        ]
        if not self.local_only:
            rows[1:1] = [
                ("/keys", "управлять API-ключами (значения скрыты)"),
                ("/provider [name]", "выбрать NVIDIA, Gemini или Ollama"),
                ("/model [name]", "выбрать модель текущего провайдера"),
            ]
        for command, description in rows:
            commands.add_row(command, description)
        footer = Text("Команды без аргумента открывают меню  ·  TAB дополняет команды", style=MUTED)
        body = Table.grid()
        body.add_row(commands)
        body.add_row(footer)
        self.output.print(Panel(body, title="[bold]Commands[/bold]", border_style=PURPLE, box=box.ROUNDED))

    def goodbye(self) -> None:
        self.output.print(Text("\nSession closed. До встречи.\n", style=MUTED))

    @staticmethod
    def _width() -> int:
        try:
            return os.get_terminal_size().columns
        except OSError:
            return 80
