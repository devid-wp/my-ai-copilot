"""Graphical-friendly Windows entry point used by the one-file executable."""

from __future__ import annotations

import sys
from pathlib import Path

from core.windows_setup import DEFAULT_LOCAL_MODEL, bootstrap_local_model
from main import main as citadex_main


def confirm(question: str) -> bool:
    answer = input(f"\n{question}\nПродолжить? [Y/n]: ").strip().casefold()
    return answer in {"", "y", "yes", "д", "да"}


def run() -> int:
    print("\nCITADEX · локальный AI-помощник\n")
    try:
        model = bootstrap_local_model(confirm)
    except (OSError, RuntimeError) as exc:
        print(f"\nОшибка настройки: {exc}", file=sys.stderr)
        if getattr(sys, "frozen", False):
            input("\nНажмите Enter, чтобы закрыть окно...")
        return 2
    return citadex_main(
        [
            "--project",
            str(Path.cwd()),
            "--provider",
            "ollama",
            "--model",
            model or DEFAULT_LOCAL_MODEL,
            "--agent",
            "--skip-setup",
        ]
    )


if __name__ == "__main__":
    raise SystemExit(run())
