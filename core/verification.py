"""Post-mutation verification before an agent reports completion."""

from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any

from core.agent_executor import run_tests


def verify_agent_changes(paths: list[str], project_root: str) -> dict[str, Any]:
    root = Path(project_root).resolve()
    checked: list[str] = []
    errors: list[str] = []
    for raw_path in dict.fromkeys(path for path in paths if path):
        path = Path(raw_path)
        path = path if path.is_absolute() else root / path
        if not path.is_file():
            errors.append(f"File missing after change: {raw_path}")
            continue
        try:
            content = path.read_text(encoding="utf-8")
            if path.suffix == ".py":
                ast.parse(content, filename=str(path))
            elif path.suffix == ".json":
                json.loads(content)
        except (OSError, SyntaxError, json.JSONDecodeError) as exc:
            errors.append(f"{raw_path}: {exc}")
        else:
            checked.append(str(path))

    test_result: dict[str, Any] | None = None
    has_tests = any(
        (root / marker).is_file()
        for marker in ("pyproject.toml", "pytest.ini", "package.json", "Cargo.toml", "go.mod")
    )
    if checked and has_tests and not errors:
        try:
            test_result = run_tests({}, project_root)
        except (OSError, RuntimeError) as exc:
            errors.append(f"Tests could not run: {exc}")
        else:
            if test_result.get("returncode") != 0:
                errors.append(f"Tests failed: {test_result.get('test_command', 'test command')}")
    return {"ok": not errors, "files": checked, "errors": errors, "tests": test_result}


__all__ = ["verify_agent_changes"]
