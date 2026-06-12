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

# Persistent working directory for execute_cmd — survives across calls in one session.
_cwd: str | None = None


def get_logger(project_root: str):
    global LOGGER
    if LOGGER is None:
        LOGGER = _setup_logger(project_root)
    return LOGGER


def _init_cwd(project_root: str) -> str:
    """Return _cwd, initialising it to project_root on first use."""
    global _cwd
    if _cwd is None:
        _cwd = os.path.normpath(os.path.abspath(project_root))
    return _cwd


# ---------------------------------------------------------------------------
# Helper to read/write files safely
# ---------------------------------------------------------------------------

def _write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _read_file(path: Path, max_bytes: int = 50 * 1024) -> str:
    data = path.read_bytes()[:max_bytes]
    return data.decode("utf-8", errors="replace")


# ---------------------------------------------------------------------------
# Executable functions – signatures match those defined in ``core/functions``
# ---------------------------------------------------------------------------

def create_file(args: Dict[str, Any], project_root: str) -> Dict[str, Any]:
    """Create (or overwrite) a file, always resolving path relative to _cwd."""
    global _cwd
    _init_cwd(project_root)

    rel_path = args["path"]
    content = args.get("content", "")

    # Resolve relative to _cwd so the agent's working directory is respected
    if os.path.isabs(rel_path):
        abs_path = os.path.normpath(rel_path)
    else:
        abs_path = os.path.normpath(os.path.join(_cwd, rel_path))

    # Security check against project root
    try:
        ensure_path_safe(abs_path, project_root)
    except Exception as e:
        return {"status": "error", "path": abs_path, "error": str(e)}

    try:
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        with open(abs_path, "w", encoding="utf-8") as f:
            f.write(content)
        if not os.path.exists(abs_path):
            return {"status": "error", "path": abs_path, "error": "File not found after write"}
        get_logger(project_root).info("create_file %s", abs_path)
        return {"status": "created", "path": abs_path, "bytes": len(content)}
    except Exception as e:
        get_logger(project_root).error("create_file failed: %s", str(e))
        return {"status": "error", "path": abs_path, "error": str(e)}


def edit_file(args: Dict[str, Any], project_root: str) -> Dict[str, Any]:
    global _cwd
    _init_cwd(project_root)

    rel_path = args["path"]
    patches: List[Dict[str, Any]] = args["patches"]

    if os.path.isabs(rel_path):
        abs_path = Path(os.path.normpath(rel_path))
    else:
        abs_path = Path(os.path.normpath(os.path.join(_cwd, rel_path)))

    try:
        ensure_path_safe(str(abs_path), project_root)
    except Exception as e:
        return {"status": "error", "path": str(abs_path), "error": str(e)}

    if not abs_path.is_file():
        return {"status": "error", "path": str(abs_path), "error": f"Файл '{rel_path}' не существует."}

    try:
        os.makedirs(abs_path.parent, exist_ok=True)
        lines = abs_path.read_text(encoding="utf-8").splitlines(keepends=True)
        for patch in sorted(patches, key=lambda p: p["start_line"]):
            start = patch["start_line"] - 1
            end = patch["end_line"]
            new_content = patch["new_content"]
            lines[start:end] = [new_content]
        abs_path.write_text("".join(lines), encoding="utf-8")
        get_logger(project_root).info("edit_file %s", abs_path)
        return {"status": "edited", "path": str(abs_path)}
    except Exception as e:
        return {"status": "error", "path": str(abs_path), "error": str(e)}


def delete_file(args: Dict[str, Any], project_root: str) -> Dict[str, Any]:
    rel_path = args["path"]
    abs_path = ensure_path_safe(os.path.join(project_root, rel_path), project_root)
    if abs_path.is_file():
        abs_path.unlink()
        get_logger(project_root).info("delete_file %s", rel_path)
        return {"result": "deleted", "path": rel_path}
    else:
        raise FileNotFoundError(f"Файл '{rel_path}' не найден.")


def make_directory(args: Dict[str, Any], project_root: str) -> Dict[str, Any]:
    """Create a directory, resolving relative paths against _cwd."""
    global _cwd
    _init_cwd(project_root)

    rel_path = args["path"]
    if os.path.isabs(rel_path):
        abs_path = os.path.normpath(rel_path)
    else:
        abs_path = os.path.normpath(os.path.join(_cwd, rel_path))

    try:
        ensure_path_safe(abs_path, project_root)
    except Exception as e:
        return {"status": "error", "path": abs_path, "error": str(e)}

    try:
        os.makedirs(abs_path, exist_ok=True)
        get_logger(project_root).info("make_directory %s", abs_path)
        return {"status": "directory_created", "path": abs_path}
    except Exception as e:
        return {"status": "error", "path": abs_path, "error": str(e)}


def execute_cmd(args: Dict[str, Any], project_root: str) -> Dict[str, Any]:
    """Execute a shell command with persistent working directory support.

    Intercepts bare ``cd <path>`` commands and updates the module-level _cwd
    without spawning a subprocess. All other commands run with cwd=_cwd.

    Returns a structured dict: {stdout, stderr, returncode, cwd}.
    """
    global _cwd
    current_cwd = _init_cwd(project_root)

    command: str = args["command"].strip()

    # ── Intercept bare cd commands ──────────────────────────────────────────
    if command == "cd" or (command.startswith("cd ") and "&&" not in command and ";" not in command):
        parts = command.split(None, 1)
        if len(parts) == 2:
            target = parts[1].strip().strip('"').strip("'")
            new_path = os.path.normpath(
                os.path.join(current_cwd, target) if not os.path.isabs(target) else target
            )
            if os.path.isdir(new_path):
                _cwd = new_path
                get_logger(project_root).info("cd → %s", _cwd)
                return {"stdout": f"Changed directory to {_cwd}", "stderr": "", "returncode": 0, "cwd": _cwd}
            else:
                return {"stdout": "", "stderr": f"cd: {target}: No such directory", "returncode": 1, "cwd": current_cwd}
        else:
            # bare "cd" with no arg — go to project root
            _cwd = os.path.normpath(os.path.abspath(project_root))
            return {"stdout": f"Changed directory to {_cwd}", "stderr": "", "returncode": 0, "cwd": _cwd}

    # ── Normal command ──────────────────────────────────────────────────────
    ensure_command_safe(command)

    try:
        proc = subprocess.run(
            command,
            shell=True,
            cwd=_cwd,
            capture_output=True,
            text=True,
            timeout=30,
        )
        get_logger(project_root).info("execute_cmd [cwd=%s] %s", _cwd, command)
        return {
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "returncode": proc.returncode,
            "cwd": str(_cwd),
        }
    except subprocess.TimeoutExpired:
        return {"stdout": "", "stderr": "Ошибка: Превышен таймаут (30 с).", "returncode": -1, "cwd": str(_cwd)}
    except Exception as e:
        return {"stdout": "", "stderr": str(e), "returncode": -1, "cwd": str(_cwd)}


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
        raise FileNotFoundError(f"Файл '{rel_path}' не найден.")
    content = _read_file(abs_path, max_bytes=50 * 1024)
    get_logger(project_root).info("read_file %s", rel_path)
    return {"result": "read", "path": rel_path, "content": content}


def search_in_files(args: Dict[str, Any], project_root: str) -> Dict[str, Any]:
    """Search for a text pattern across all project source files."""
    pattern = args["pattern"]
    path = args.get("path", "")
    search_root = os.path.normpath(os.path.join(project_root, path)) if path else project_root

    results = []
    skip_dirs = {'.git', '__pycache__', 'node_modules', 'venv', '.pytest_cache', 'logs', '~'}
    exts = ('.py', '.js', '.ts', '.json', '.md', '.txt', '.yaml', '.yml', '.toml', '.bat', '.sh')

    for root, dirs, files in os.walk(search_root):
        dirs[:] = [d for d in dirs if d not in skip_dirs and not d.startswith('.')]
        for fname in files:
            if not fname.endswith(exts):
                continue
            fpath = os.path.join(root, fname)
            try:
                with open(fpath, 'r', encoding='utf-8', errors='replace') as f:
                    for i, line in enumerate(f, 1):
                        if pattern.lower() in line.lower():
                            rel = os.path.relpath(fpath, project_root)
                            results.append(f"{rel}:{i}: {line.rstrip()}")
            except Exception:
                continue

    get_logger(project_root).info("search_in_files pattern=%s", pattern)

    if not results:
        return {"result": "not_found", "pattern": pattern, "matches": []}
    return {"result": "found", "pattern": pattern, "count": len(results), "matches": results[:80]}


# Mapping from function name (as sent by the model) to the Python implementation.
FUNCTION_MAP = {
    "create_file": create_file,
    "edit_file": edit_file,
    "delete_file": delete_file,
    "make_directory": make_directory,
    "execute_cmd": execute_cmd,
    "list_directory": list_directory,
    "read_file": read_file,
    "search_in_files": search_in_files,
}


def dispatch_function(name: str, args: Dict[str, Any], project_root: str) -> Dict[str, Any]:
    """Call the appropriate function and return a JSON-serialisable dict.

    Shows a status line before execution so the user knows what the agent is doing.
    Any exception is caught and turned into an ``error`` field so the model can react to it.
    """
    from ui.screen import show_tool_status  # late import to avoid circular deps

    func = FUNCTION_MAP.get(name)
    if func is None:
        raise ValueError(f"Неподдерживаемая функция '{name}'.")

    # Show human-readable status: ⏳ Выполняю: create_file для src/main.py
    path_hint = args.get("path") or args.get("command") or ""
    show_tool_status(name, str(path_hint))

    try:
        return func(args, project_root)
    except Exception as e:
        get_logger(project_root).error("Function %s failed: %s", name, str(e))
        return {"error": str(e)}
