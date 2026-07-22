"""Fast, deterministic project environment detection."""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import tomllib  # type: ignore[import-not-found]
except ModuleNotFoundError:  # Python 3.10
    import tomli as tomllib  # type: ignore[import-not-found]


@dataclass(frozen=True, slots=True)
class ProjectEnvironment:
    languages: tuple[str, ...]
    frameworks: tuple[str, ...]
    run_commands: tuple[str, ...]
    test_commands: tuple[str, ...]
    git_status: str
    config_files: tuple[str, ...]

    def render(self) -> str:
        def show(values: tuple[str, ...]) -> str:
            return ", ".join(values) or "unknown"

        return "\n".join(
            (
                "Project environment:",
                f"Languages: {show(self.languages)}",
                f"Frameworks: {show(self.frameworks)}",
                f"Run commands: {show(self.run_commands)}",
                f"Test commands: {show(self.test_commands)}",
                f"Git status: {self.git_status}",
                f"Important config: {show(self.config_files)}",
            )
        )


def detect_project_environment(project_root: str) -> ProjectEnvironment:
    root = Path(project_root).resolve()
    languages: set[str] = set()
    frameworks: set[str] = set()
    run_commands: list[str] = []
    test_commands: list[str] = []
    important = (
        "pyproject.toml",
        "requirements.txt",
        "setup.py",
        "package.json",
        "tsconfig.json",
        "Cargo.toml",
        "go.mod",
        "pom.xml",
        "Dockerfile",
        "Makefile",
    )
    configs = tuple(name for name in important if (root / name).is_file())

    pyproject = root / "pyproject.toml"
    if pyproject.is_file():
        languages.add("Python")
        try:
            data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
        except (OSError, tomllib.TOMLDecodeError):
            data = {}
        dependencies = " ".join(data.get("project", {}).get("dependencies", [])).casefold()
        for dependency_name, framework in (
            ("django", "Django"),
            ("fastapi", "FastAPI"),
            ("flask", "Flask"),
        ):
            if dependency_name in dependencies:
                frameworks.add(framework)
        run_commands.append("python -m <package>")
        test_commands.append("pytest")

    package_json = root / "package.json"
    if package_json.is_file():
        languages.add("TypeScript" if (root / "tsconfig.json").is_file() else "JavaScript")
        try:
            package_data: dict[str, Any] = json.loads(package_json.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            package_data = {}
        node_dependencies = {
            **package_data.get("dependencies", {}),
            **package_data.get("devDependencies", {}),
        }
        for name, framework in (
            ("next", "Next.js"),
            ("react", "React"),
            ("vue", "Vue"),
            ("@angular/core", "Angular"),
        ):
            if name in node_dependencies:
                frameworks.add(framework)
        scripts = package_data.get("scripts", {})
        run_commands.extend(f"npm run {name}" for name in ("dev", "start", "build") if name in scripts)
        test_commands.extend(f"npm run {name}" for name in ("test", "test:unit") if name in scripts)

    for marker, language in (("Cargo.toml", "Rust"), ("go.mod", "Go"), ("pom.xml", "Java")):
        if (root / marker).is_file():
            languages.add(language)
    try:
        result = subprocess.run(
            ["git", "status", "--short", "--branch"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=5,
        )
        git_status = result.stdout.strip() or "clean" if result.returncode == 0 else "not a repository"
    except (OSError, subprocess.SubprocessError):
        git_status = "unavailable"
    return ProjectEnvironment(
        tuple(sorted(languages)),
        tuple(sorted(frameworks)),
        tuple(run_commands),
        tuple(test_commands),
        git_status,
        configs,
    )


__all__ = ["ProjectEnvironment", "detect_project_environment"]
