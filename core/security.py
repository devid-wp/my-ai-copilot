"""Security boundaries for filesystem and command tools."""

from __future__ import annotations

import logging
import os
import re
import shlex
from collections.abc import Callable
from pathlib import Path

ALLOWED_COMMANDS = {
    "python",
    "python3",
    "pytest",
    "git",
    "pip",
    "pip3",
    "npm",
    "node",
    "cargo",
    "go",
    "ls",
    "dir",
    "echo",
    "cat",
}

PROTECTED_NAMES = {".git", ".env", ".env.local", ".env.production"}
SHELL_META_RE = re.compile(r"(?:&&|\|\||[;|<>`]|\$\(|\r|\n)")

ApprovalCallback = Callable[[str, str], bool]


def parse_command(command: str) -> list[str]:
    """Return a safe argv list or raise ``PermissionError``.

    Shell syntax is deliberately unsupported. Commands are executed with
    ``shell=False`` by the executor, so validating only the first token is not
    enough: this function also rejects chaining, redirects and substitutions.
    """
    command = command.strip()
    if not command or SHELL_META_RE.search(command):
        raise PermissionError("Shell operators, redirects and empty commands are not allowed.")
    try:
        argv = shlex.split(command, posix=os.name != "nt")
    except ValueError as exc:
        raise PermissionError(f"Invalid command syntax: {exc}") from exc
    if not argv:
        raise PermissionError("Empty command is not allowed.")
    if os.name == "nt":
        argv = [
            item[1:-1] if len(item) >= 2 and item[0] == item[-1] and item[0] in {'"', "'"} else item
            for item in argv
        ]
    executable = Path(argv[0].strip('"')).name.lower()
    if executable.endswith(".exe"):
        executable = executable[:-4]
    if executable not in ALLOWED_COMMANDS:
        raise PermissionError(
            f"Command '{executable}' is not allowed. Allowed commands: {', '.join(sorted(ALLOWED_COMMANDS))}"
        )
    # Interpreter escape hatches turn a small allowlist into arbitrary execution.
    lowered = [item.lower() for item in argv[1:]]
    if executable in {"python", "python3", "node"} and any(
        item in {"-c", "-e", "--eval"} for item in lowered
    ):
        raise PermissionError("Inline interpreter code is not allowed.")
    if (
        executable == "git"
        and lowered
        and lowered[0]
        in {
            "clean",
            "reset",
            "checkout",
            "restore",
            "rebase",
            "push",
        }
    ):
        raise PermissionError(f"Destructive git subcommand '{lowered[0]}' is not allowed.")
    return argv


def is_command_allowed(command: str) -> bool:
    try:
        parse_command(command)
        return True
    except PermissionError:
        return False


def is_path_inside_root(path: str | os.PathLike[str], root: str | os.PathLike[str]) -> bool:
    root_path = Path(root).resolve()
    target_path = Path(path).resolve()
    try:
        target_path.relative_to(root_path)
        return True
    except ValueError:
        return False


def ensure_path_safe(path: str | os.PathLike[str], root: str | os.PathLike[str]) -> Path:
    target = Path(path).resolve()
    if not is_path_inside_root(target, root):
        raise PermissionError(f"Path '{path}' is outside project root '{root}'.")
    return target


def ensure_mutation_safe(path: str | os.PathLike[str], root: str | os.PathLike[str]) -> Path:
    target = ensure_path_safe(path, root)
    root_path = Path(root).resolve()
    if target == root_path:
        raise PermissionError("The project root cannot be modified or deleted.")
    relative_parts = target.relative_to(root_path).parts
    if any(part.lower() in PROTECTED_NAMES for part in relative_parts):
        raise PermissionError(f"Protected path cannot be modified: '{target}'.")
    return target


def ensure_command_safe(command: str) -> str:
    parse_command(command)
    return command


def require_approval(
    callback: ApprovalCallback | None,
    action: str,
    detail: str,
) -> None:
    if callback is None or not callback(action, detail):
        raise PermissionError(f"User approval required for {action}: {detail}")


def _setup_logger(project_root: str) -> logging.Logger:
    log_dir = Path(project_root) / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger(f"citadex.agent.{Path(project_root).resolve()}")
    if not logger.handlers:
        handler = logging.FileHandler(log_dir / "agent.log", encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False
    return logger


def close_project_logger(project_root: str) -> None:
    """Release file handles for disposable projects such as smoke-test sandboxes."""
    logger = logging.getLogger(f"citadex.agent.{Path(project_root).resolve()}")
    for handler in tuple(logger.handlers):
        handler.close()
        logger.removeHandler(handler)


__all__ = [
    "ALLOWED_COMMANDS",
    "ApprovalCallback",
    "ensure_command_safe",
    "ensure_mutation_safe",
    "ensure_path_safe",
    "is_command_allowed",
    "is_path_inside_root",
    "parse_command",
    "require_approval",
    "close_project_logger",
    "_setup_logger",
]
