"""Citadex-specific project ignore rules."""

from __future__ import annotations

from fnmatch import fnmatch
from pathlib import Path

DEFAULT_IGNORE_RULES = (".venv/", "node_modules/", "dist/", "build/", ".env", "*.key")


def load_ignore_rules(project_root: str) -> tuple[str, ...]:
    path = Path(project_root) / ".citadexignore"
    try:
        custom = tuple(
            line.strip() for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        )
    except OSError:
        custom = ()
    return (*DEFAULT_IGNORE_RULES, *custom)


def is_ignored_path(path: str | Path, project_root: str, rules: tuple[str, ...] | None = None) -> bool:
    root = Path(project_root).resolve()
    candidate = Path(path).resolve()
    try:
        relative = candidate.relative_to(root).as_posix()
    except ValueError:
        return True
    active = rules or load_ignore_rules(project_root)
    parts = relative.split("/")
    for rule in active:
        normalized = rule.replace("\\", "/").lstrip("/")
        if normalized.endswith("/"):
            directory = normalized.rstrip("/")
            if directory in parts[:-1] or relative == directory:
                return True
        elif fnmatch(relative, normalized) or fnmatch(candidate.name, normalized):
            return True
    return False


__all__ = ["DEFAULT_IGNORE_RULES", "is_ignored_path", "load_ignore_rules"]
