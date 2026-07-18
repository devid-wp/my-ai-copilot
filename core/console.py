"""Small, dependency-light terminal interface for Citadex."""

from __future__ import annotations

import os
import sys
from collections.abc import Iterable
from typing import Any

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.styles import Style

PURPLE = "\033[38;5;141m"
CYAN = "\033[38;5;81m"
GREEN = "\033[38;5;78m"
YELLOW = "\033[38;5;221m"
RED = "\033[38;5;203m"
DIM = "\033[2m"
BOLD = "\033[1m"
RESET = "\033[0m"


class Console:
    def __init__(self) -> None:
        self.session: PromptSession[str] | None = None
        if sys.stdin.isatty() and sys.stdout.isatty():
            self.session = PromptSession(
                multiline=False,
                completer=WordCompleter(
                    [
                        "/provider",
                        "/model",
                        "/mode",
                        "/permissions",
                        "/status",
                        "/clear",
                        "/help",
                        "/exit",
                    ],
                    sentence=True,
                ),
                complete_while_typing=True,
                style=Style.from_dict({"prompt": "ansicyan bold", "path": "ansibrightblack"}),
            )

    def header(self, provider: str, model: str, project: str, agent: bool) -> None:
        width = min(88, max(54, self._width()))
        mode = "AGENT" if agent else "CHAT"
        print(f"\n{PURPLE}{BOLD}╭{'─' * (width - 2)}╮{RESET}")
        print(
            f"{PURPLE}{BOLD}│{RESET}  CITADEX  {DIM}terminal coding copilot{RESET}".ljust(width + 20)
            + f"{PURPLE}{BOLD}│{RESET}"
        )
        print(f"{PURPLE}{BOLD}╰{'─' * (width - 2)}╯{RESET}")
        print(f"  {CYAN}●{RESET} {provider} / {model}   {DIM}[{mode}]{RESET}")
        print(f"  {DIM}{project}{RESET}\n")

    def prompt(self) -> str:
        return self._read("❯ ", HTML("<prompt>❯ </prompt>"))

    def choose(self, title: str, options: list[str]) -> str:
        print(f"\n  {BOLD}{title}{RESET}")
        for index, option in enumerate(options, 1):
            print(f"  {PURPLE}{index}{RESET}  {option}")
        while True:
            answer = self._read("  Select › ", HTML("<prompt>  Select › </prompt>")).strip()
            if answer in options:
                return answer
            if answer.isdigit() and 1 <= int(answer) <= len(options):
                return options[int(answer) - 1]
            self.error("Введите номер или название из списка")

    def hint(self, message: str) -> None:
        print(f"  {DIM}{message}{RESET}\n")

    def status(self, provider: str, model: str, mode: str, permissions: str) -> None:
        print(f"""
  {DIM}provider{RESET}     {provider}
  {DIM}model{RESET}        {model}
  {DIM}mode{RESET}         {mode}
  {DIM}permissions{RESET}  {permissions}
""")

    def stream(self, tokens: Iterable[str]) -> str:
        print(f"{PURPLE}┃{RESET} ", end="", flush=True)
        parts: list[str] = []
        for token in tokens:
            parts.append(token)
            print(token, end="", flush=True)
        print("\n")
        return "".join(parts)

    def step(self, current: int, total: int, model: str) -> None:
        print(f"{DIM}step {current}/{total} · {model}{RESET}")

    def tool(self, name: str, detail: str) -> None:
        print(f"  {CYAN}◆{RESET} {name} {DIM}{detail}{RESET}")

    def tool_result(self, result: dict[str, Any]) -> None:
        if result.get("status") == "error" or "error" in result:
            self.error(str(result.get("error", "unknown error")))
        else:
            label = result.get("status", "ok")
            print(f"  {GREEN}✓{RESET} {label}")

    def confirm(self, action: str, detail: str) -> bool:
        print(f"\n  {YELLOW}Approval required{RESET}")
        print(f"  {BOLD}{action}{RESET}: {detail}")
        answer = self._read("  Allow? [y/N] ", HTML("<prompt>  Allow? [y/N] </prompt>"))
        return answer.strip().lower() in {"y", "yes", "д", "да"}

    def _read(self, plain_prompt: str, rich_prompt: HTML) -> str:
        if self.session is None:
            return input(plain_prompt)
        return self.session.prompt(rich_prompt)

    def success(self, message: str) -> None:
        print(f"{GREEN}✓ {message}{RESET}\n")

    def warning(self, message: str) -> None:
        print(f"{YELLOW}! {message}{RESET}\n")

    def error(self, message: str) -> None:
        print(f"{RED}✗ {message}{RESET}\n", file=sys.stderr)

    def help(self) -> None:
        print("""
  /provider [name]       выбрать NVIDIA, Gemini или Ollama
  /model [name]          выбрать модель текущего провайдера
  /mode [chat|agent]     переключить чат и агентный режим
  /permissions [ask|auto]
                         настроить подтверждения действий
  /status                показать настройки текущей сессии
  /clear                 очистить историю
  /help                  показать справку
  /exit                  выйти

  Можно вызвать /provider, /model, /mode и /permissions без аргумента —
  Citadex покажет интерактивное меню. Флаги CLI нужны только для автоматизации.
""")

    def goodbye(self) -> None:
        print(f"\n{DIM}До встречи.{RESET}\n")

    @staticmethod
    def _width() -> int:
        try:
            return os.get_terminal_size().columns
        except OSError:
            return 80
