"""Rich terminal interface for Citadex."""

from __future__ import annotations

import os
import sys
from collections.abc import Iterable
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

PURPLE = "#a78bfa"
PURPLE_DARK = "#7c3aed"
CYAN = "#22d3ee"
GREEN = "#4ade80"
YELLOW = "#facc15"
RED = "#fb7185"
MUTED = "#71717a"
SURFACE = "#18181b"

SLASH_COMMANDS = [
    "/provider",
    "/model",
    "/mode",
    "/permissions",
    "/status",
    "/clear",
    "/help",
    "/exit",
]


class Console:
    def __init__(self) -> None:
        self.output = RichConsole(highlight=False, soft_wrap=True)
        self.session: PromptSession[str] | None = None
        if sys.stdin.isatty() and sys.stdout.isatty():
            self.session = PromptSession(
                multiline=False,
                completer=WordCompleter(SLASH_COMMANDS, sentence=True),
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

    def choose(self, title: str, options: list[str]) -> str:
        menu = Table(box=box.SIMPLE, show_header=False, padding=(0, 1), border_style=MUTED)
        menu.add_column("number", justify="right", style=f"bold {PURPLE}", width=3)
        menu.add_column("option", style="white")
        for index, option in enumerate(options, 1):
            menu.add_row(str(index), option)
        self.output.print(Panel(menu, title=f"[bold]{title}[/bold]", border_style=PURPLE, box=box.ROUNDED))
        while True:
            answer = self._read("select ❯ ", HTML("<brand>select</brand> <prompt>❯</prompt> ")).strip()
            if answer in options:
                return answer
            if answer.isdigit() and 1 <= int(answer) <= len(options):
                return options[int(answer) - 1]
            self.error("Введите номер или название из списка")

    def hint(self, _message: str) -> None:
        hint = Text()
        for index, command in enumerate(SLASH_COMMANDS[:5]):
            if index:
                hint.append("  ·  ", style=MUTED)
            hint.append(command, style=PURPLE)
        hint.append("    TAB to complete", style=f"italic {MUTED}")
        self.output.print(hint)
        self.output.print()

    def status(self, provider: str, model: str, mode: str, permissions: str) -> None:
        table = Table.grid(padding=(0, 2))
        table.add_column(style=MUTED)
        table.add_column(style="bold white")
        table.add_row("provider", provider)
        table.add_row("model", model)
        table.add_row("mode", Text(mode, style=PURPLE if mode == "agent" else CYAN))
        table.add_row("permissions", Text(permissions, style=YELLOW if permissions == "auto" else GREEN))
        self.output.print(Panel(table, title="[bold]Session[/bold]", border_style=MUTED, box=box.ROUNDED))

    def stream(self, tokens: Iterable[str]) -> str:
        parts: list[str] = []
        self.output.print(Text("CITADEX", style=f"bold {PURPLE}"), end=" ")
        for token in tokens:
            parts.append(token)
            self.output.print(token, end="", markup=False, highlight=False)
        self.output.print("\n")
        return "".join(parts)

    def step(self, current: int, total: int, model: str) -> None:
        self.output.print(
            Text.assemble(
                (f"STEP {current}/{total}", f"bold {PURPLE}"),
                ("  ·  ", MUTED),
                (model, MUTED),
            )
        )

    def tool(self, name: str, detail: str) -> None:
        self.output.print(Text.assemble(("◆ ", CYAN), (name, "bold white"), (f"  {detail}", MUTED)))

    def tool_result(self, result: dict[str, Any]) -> None:
        if result.get("status") == "error" or "error" in result:
            self.error(str(result.get("error", "unknown error")))
        else:
            self.output.print(Text.assemble(("  ✓ ", GREEN), (str(result.get("status", "ok")), MUTED)))

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
        return self.session.prompt(rich_prompt)

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
            ("/provider [name]", "выбрать NVIDIA, Gemini или Ollama"),
            ("/model [name]", "выбрать модель текущего провайдера"),
            ("/mode [chat|agent]", "переключить режим работы"),
            ("/permissions [ask|auto]", "настроить подтверждения действий"),
            ("/status", "показать настройки сессии"),
            ("/clear", "очистить историю"),
            ("/exit", "выйти"),
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
