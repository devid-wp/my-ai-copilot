"""Safe execution layer for model-requested tools."""

from __future__ import annotations

import os
import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any

from core.security import (
    ApprovalCallback,
    _setup_logger,
    ensure_mutation_safe,
    ensure_path_safe,
    parse_command,
    require_approval,
)

MAX_READ_BYTES = 50 * 1024
MAX_OUTPUT_CHARS = 20_000


def _target(project_root: str, raw_path: str, *, mutation: bool = False) -> Path:
    root = Path(project_root).resolve()
    raw = Path(raw_path)
    candidate = raw if raw.is_absolute() else root / raw
    validator = ensure_mutation_safe if mutation else ensure_path_safe
    return validator(candidate, root)


def _approved(callback: ApprovalCallback | None, action: str, detail: str) -> None:
    require_approval(callback, action, detail)


def create_file(
    args: dict[str, Any],
    project_root: str,
    approve: ApprovalCallback | None = None,
) -> dict[str, Any]:
    path = _target(project_root, str(args["path"]), mutation=True)
    exists = path.exists()
    _approved(approve, "overwrite file" if exists else "create file", str(path))
    path.parent.mkdir(parents=True, exist_ok=True)
    content = str(args.get("content", ""))
    temporary = path.with_name(f".{path.name}.citadex.tmp")
    temporary.write_text(content, encoding="utf-8", newline="\n")
    temporary.replace(path)
    _setup_logger(project_root).info("create_file %s", path)
    return {
        "status": "updated" if exists else "created",
        "path": str(path),
        "bytes": len(content.encode("utf-8")),
    }


def edit_file(
    args: dict[str, Any],
    project_root: str,
    approve: ApprovalCallback | None = None,
) -> dict[str, Any]:
    path = _target(project_root, str(args["path"]), mutation=True)
    if not path.is_file():
        raise FileNotFoundError(f"File not found: {args['path']}")
    patches = list(args.get("patches") or [])
    if not patches:
        raise ValueError("At least one patch is required.")
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    normalized: list[tuple[int, int, str]] = []
    for patch in patches:
        start = int(patch["start_line"])
        end = int(patch["end_line"])
        if start < 1 or end < start or end > len(lines) + 1:
            raise ValueError(f"Invalid line range [{start}, {end}) for {len(lines)} lines.")
        normalized.append((start, end, str(patch["new_content"])))
    ordered = sorted(normalized, reverse=True)
    for index in range(len(ordered) - 1):
        later_start, _, _ = ordered[index]
        _, earlier_end, _ = ordered[index + 1]
        if earlier_end > later_start:
            raise ValueError("Overlapping patches are not allowed.")
    _approved(approve, "edit file", f"{path} ({len(ordered)} patch(es))")
    for start, end, replacement in ordered:
        lines[start - 1 : end - 1] = [replacement]
    temporary = path.with_name(f".{path.name}.citadex.tmp")
    temporary.write_text("".join(lines), encoding="utf-8", newline="\n")
    temporary.replace(path)
    _setup_logger(project_root).info("edit_file %s", path)
    return {"status": "edited", "path": str(path), "patches": len(ordered)}


def delete_file(
    args: dict[str, Any],
    project_root: str,
    approve: ApprovalCallback | None = None,
) -> dict[str, Any]:
    path = _target(project_root, str(args["path"]), mutation=True)
    if not path.exists():
        raise FileNotFoundError(f"Path not found: {args['path']}")
    action = "delete directory" if path.is_dir() else "delete file"
    _approved(approve, action, str(path))
    if path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink()
    _setup_logger(project_root).info("%s %s", action.replace(" ", "_"), path)
    return {"status": "deleted", "path": str(path)}


def make_directory(
    args: dict[str, Any],
    project_root: str,
    approve: ApprovalCallback | None = None,
) -> dict[str, Any]:
    path = _target(project_root, str(args["path"]), mutation=True)
    _approved(approve, "create directory", str(path))
    path.mkdir(parents=True, exist_ok=True)
    _setup_logger(project_root).info("make_directory %s", path)
    return {"status": "directory_created", "path": str(path)}


def execute_cmd(
    args: dict[str, Any],
    project_root: str,
    approve: ApprovalCallback | None = None,
) -> dict[str, Any]:
    command = str(args["command"])
    argv = parse_command(command)
    _approved(approve, "execute command", command)
    try:
        result = subprocess.run(
            argv,
            shell=False,
            cwd=Path(project_root).resolve(),
            capture_output=True,
            text=True,
            timeout=30,
        )
        _setup_logger(project_root).info("execute_cmd %s", command)
        return {
            "stdout": result.stdout[-MAX_OUTPUT_CHARS:],
            "stderr": result.stderr[-MAX_OUTPUT_CHARS:],
            "returncode": result.returncode,
            "cwd": str(Path(project_root).resolve()),
            "truncated": len(result.stdout) > MAX_OUTPUT_CHARS or len(result.stderr) > MAX_OUTPUT_CHARS,
        }
    except subprocess.TimeoutExpired:
        return {
            "stdout": "",
            "stderr": "Command timed out after 30 seconds.",
            "returncode": -1,
            "cwd": str(Path(project_root).resolve()),
        }


def list_directory(
    args: dict[str, Any],
    project_root: str,
    approve: ApprovalCallback | None = None,
) -> dict[str, Any]:
    path = _target(project_root, str(args.get("path", "")))
    if not path.is_dir():
        raise NotADirectoryError(str(path))
    entries: list[dict[str, str | bool]] = sorted(
        ({"name": item.name, "is_dir": item.is_dir()} for item in path.iterdir()),
        key=lambda item: (not item["is_dir"], str(item["name"]).lower()),
    )
    return {"status": "listed", "path": str(path), "entries": entries}


def read_file(
    args: dict[str, Any],
    project_root: str,
    approve: ApprovalCallback | None = None,
) -> dict[str, Any]:
    path = _target(project_root, str(args["path"]))
    if not path.is_file():
        raise FileNotFoundError(str(path))
    data = path.read_bytes()[:MAX_READ_BYTES]
    return {
        "status": "read",
        "path": str(path),
        "content": data.decode("utf-8", errors="replace"),
        "truncated": path.stat().st_size > MAX_READ_BYTES,
    }


def search_in_files(
    args: dict[str, Any],
    project_root: str,
    approve: ApprovalCallback | None = None,
) -> dict[str, Any]:
    root = _target(project_root, str(args.get("path", "")))
    pattern = str(args["pattern"]).casefold()
    matches: list[str] = []
    skip = {".git", ".venv", "venv", "node_modules", "logs", "__pycache__"}
    extensions = {".py", ".js", ".ts", ".json", ".md", ".toml", ".yaml", ".yml", ".sh", ".ps1", ".bat"}
    for current, dirs, files in os.walk(root):
        dirs[:] = [name for name in dirs if name not in skip and not name.startswith(".")]
        for name in files:
            path = Path(current) / name
            if path.suffix.lower() not in extensions:
                continue
            try:
                for number, line in enumerate(
                    path.read_text(encoding="utf-8", errors="replace").splitlines(), 1
                ):
                    if pattern in line.casefold():
                        matches.append(f"{path.relative_to(project_root)}:{number}: {line}")
                        if len(matches) >= 80:
                            return {
                                "status": "found",
                                "count": len(matches),
                                "matches": matches,
                                "truncated": True,
                            }
            except OSError:
                continue
    return {
        "status": "found" if matches else "not_found",
        "count": len(matches),
        "matches": matches,
        "truncated": False,
    }


FUNCTION_MAP: dict[str, Callable[..., dict[str, Any]]] = {
    "create_file": create_file,
    "edit_file": edit_file,
    "delete_file": delete_file,
    "make_directory": make_directory,
    "execute_cmd": execute_cmd,
    "list_directory": list_directory,
    "read_file": read_file,
    "search_in_files": search_in_files,
}


def dispatch_function(
    name: str,
    args: dict[str, Any],
    project_root: str,
    approve: ApprovalCallback | None = None,
) -> dict[str, Any]:
    function = FUNCTION_MAP.get(name)
    if function is None:
        raise ValueError(f"Unsupported function: {name}")
    try:
        return function(args, project_root, approve)
    except Exception as exc:
        _setup_logger(project_root).warning("%s denied or failed: %s", name, exc)
        return {"status": "error", "error": str(exc)}
