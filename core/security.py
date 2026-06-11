"""Security utilities for the autonomous agent.

* Path validation – ensures that any supplied relative path stays inside the
  configured project root (prevents path‑traversal attacks).
* Command whitelist – only a predefined set of development tools is allowed.

Both helpers raise ``PermissionError`` with a user‑friendly message when the check
fails. The functions are used by the implementation in ``core/agent_executor``
(and indirectly by the function wrappers in ``core/functions``).
"""
import os
import pathlib
from typing import List

# ---------------------------------------------------------------------------
# Configuration (hard‑coded per user request)
# ---------------------------------------------------------------------------
ALLOWED_COMMANDS: List[str] = [
    "python",
    "git",
    "pip",
    "npm",
    "node",
    "cargo",
    "go",
    "ls",
    "dir",
    "echo",
    "cat",
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def is_command_allowed(command: str) -> bool:
    """Return ``True`` if the first token of *command* is in ``ALLOWED_COMMANDS``.

    The check is case‑insensitive and ignores leading whitespace.
    """
    if not command:
        return False
    cmd = command.strip().split()[0].lower()
    return cmd in ALLOWED_COMMANDS


def is_path_inside_root(path: str, root: str) -> bool:
    """Validate that *path* resolves inside *root*.

    ``path`` can be absolute or relative. The function resolves the absolute
    path and then checks that the resulting path starts with the absolute root
    directory. ``..`` components that would escape the root cause ``False``.
    """
    # Resolve both to absolute, normalized paths
    root_path = pathlib.Path(root).resolve()
    target_path = pathlib.Path(path).resolve()
    try:
        target_path.relative_to(root_path)
        return True
    except ValueError:
        return False


def ensure_path_safe(path: str, root: str) -> pathlib.Path:
    """Return a ``Path`` object for *path* after validation.

    Raises ``PermissionError`` with a clear message if the validation fails.
    """
    if not is_path_inside_root(path, root):
        raise PermissionError(
            f"Доступ к '{path}' запрещен – путь лежит за пределами корня проекта '{root}'."
        )
    return pathlib.Path(path).resolve()


def ensure_command_safe(command: str) -> str:
    """Validate *command* against the whitelist.

    Returns the original command when allowed, otherwise raises ``PermissionError``.
    """
    if not is_command_allowed(command):
        raise PermissionError(
            f"Команда '{command}' не разрешена. Разрешенные команды: {', '.join(ALLOWED_COMMANDS)}"
        )
    return command


import logging
import os as _os


def _setup_logger(project_root: str) -> logging.Logger:
    """Create (or reuse) a file logger writing to <project_root>/logs/agent.log."""
    log_dir = _os.path.join(project_root, "logs")
    _os.makedirs(log_dir, exist_ok=True)
    log_file = _os.path.join(log_dir, "agent.log")

    logger = logging.getLogger("agent")
    if not logger.handlers:
        handler = logging.FileHandler(log_file, encoding="utf-8")
        handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
        )
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
    return logger


__all__ = [
    "ALLOWED_COMMANDS",
    "is_command_allowed",
    "is_path_inside_root",
    "ensure_path_safe",
    "ensure_command_safe",
    "_setup_logger",
]
