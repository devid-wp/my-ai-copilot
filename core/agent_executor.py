"""Agent executor – bridges OpenAI function calls to actual Python operations.

The executor is deliberately thin: each function validates inputs via ``core.security``
and then performs the requested action. Results are returned as dictionaries that
will be sent back to the model with ``role='tool'``.

All actions are logged to ``logs/agent.log`` using the shared logger from
``core.security`` (setup via ``_setup_logger``).
"""

import os
import subprocess
import json
from pathlib import Path
from typing import Any, Dict, List

from core.security import (
    ensure_path_safe,
    ensure_command_safe,
    _setup_logger,
)

# Global logger – will be initialised on first call with the project root.
LOGGER = None


def get_logger(project_root: str):
    global LOGGER
    if LOGGER is None:
        LOGGER = _setup_logger(project_root)
    return LOGGER


# ---------------------------------------------------------------------------
# Helper to read/write files safely
# ---------------------------------------------------------------------------

def _write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _read_file(path: Path, max_bytes: int = 5 * 1024) -> str:
    data = path.read_bytes()[:max_bytes]
    return data.decode("utf-8", errors="replace")


# ---------------------------------------------------------------------------
# Executable functions – signatures match those defined in ``core/functions``
# ---------------------------------------------------------------------------

def create_file(args: Dict[str, Any], project_root: str) -> Dict[str, Any]:
    rel_path = args["path"]
    content = args["content"]
    abs_path = ensure_path_safe(os.path.join(project_root, rel_path), project_root)
    _write_file(abs_path, content)
    get_logger(project_root).info("create_file %s", rel_path)
    return {"result": "created", "path": rel_path}


def edit_file(args: Dict[str, Any], project_root: str) -> Dict[str, Any]:
    rel_path = args["path"]
    patches: List[Dict[str, Any]] = args["patches"]
    abs_path = ensure_path_safe(os.path.join(project_root, rel_path), project_root)
    if not abs_path.is_file():
        raise FileNotFoundError(f"File '{rel_path}' does not exist.")
    lines = abs_path.read_text(encoding="utf-8").splitlines(keepends=True)
    for patch in sorted(patches, key=lambda p: p["start_line"]):
        start = patch["start_line"] - 1
        end = patch["end_line"]
        new_content = patch["new_content"]
        lines[start:end] = [new_content]
    abs_path.write_text("".join(lines), encoding="utf-8")
    get_logger(project_root).info("edit_file %s", rel_path)
    return {"result": "edited", "path": rel_path}


def delete_file(args: Dict[str, Any], project_root: str) -> Dict[str, Any]:
    rel_path = args["path"]
    abs_path = ensure_path_safe(os.path.join(project_root, rel_path), project_root)
    if abs_path.is_file():
        abs_path.unlink()
        get_logger(project_root).info("delete_file %s", rel_path)
        return {"result": "deleted", "path": rel_path}
    else:
        raise FileNotFoundError(f"File '{rel_path}' not found.")


def make_directory(args: Dict[str, Any], project_root: str) -> Dict[str, Any]:
    rel_path = args["path"]
    abs_path = ensure_path_safe(os.path.join(project_root, rel_path), project_root)
    abs_path.mkdir(parents=True, exist_ok=True)
    get_logger(project_root).info("make_directory %s", rel_path)
    return {"result": "directory_created", "path": rel_path}


def execute_cmd(args: Dict[str, Any], project_root: str) -> Dict[str, Any]:
    command = args["command"]
    ensure_command_safe(command)
    proc = subprocess.run(
        command,
        shell=True,
        cwd=project_root,
        capture_output=True,
        text=True,
        timeout=30,
    )
    get_logger(project_root).info("execute_cmd %s", command)
    return {
        "result": "executed",
        "command": command,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "returncode": proc.returncode,
    }


def list_directory(args: Dict[str, Any], project_root: str) -> Dict[str, Any]:
    rel_path = args.get("path", "")
    abs_path = ensure_path_safe(os.path.join(project_root, rel_path), project_root)
    entries = [{"name": e.name, "is_dir": e.is_dir()} for e in abs_path.iterdir()]
    get_logger(project_root).info("list_directory %s", rel_path)
    return {"result": "listed", "path": rel_path, "entries": entries}


def read_file(args: Dict[str, Any], project_root: str) -> Dict[str, Any]:
    rel_path = args["path"]
    abs_path = ensure_path_safe(os.path.join(project_root, rel_path), project_root)
    if not abs_path.is_file():
        raise FileNotFoundError(f"File '{rel_path}' not found.")
    content = _read_file(abs_path)
    get_logger(project_root).info("read_file %s", rel_path)
    return {"result": "read", "path": rel_path, "content": content}


# Mapping from function name (as sent by the model) to the Python implementation.
FUNCTION_MAP = {
    "create_file": create_file,
    "edit_file": edit_file,
    "delete_file": delete_file,
    "make_directory": make_directory,
    "execute_cmd": execute_cmd,
    "list_directory": list_directory,
    "read_file": read_file,
}


def dispatch_function(name: str, args: Dict[str, Any], project_root: str) -> Dict[str, Any]:
    """Call the appropriate function and return a JSON-serialisable dict.

    Shows a status line before execution so the user knows what the agent is doing.
    Any exception is caught and turned into an ``error`` field so the model can react to it.
    """
    from ui.screen import show_tool_status  # late import to avoid circular deps

    func = FUNCTION_MAP.get(name)
    if func is None:
        raise ValueError(f"Unsupported function '{name}'.")

    # Show human-readable status: ⏳ Выполняю: create_file для src/main.py
    path_hint = args.get("path") or args.get("command") or ""
    show_tool_status(name, str(path_hint))

    try:
        return func(args, project_root)
    except Exception as e:
        get_logger(project_root).error("Function %s failed: %s", name, str(e))
        return {"error": str(e)}
