# core/context_manager.py
"""
Сканер проекта.
Читает структуру каталогов и содержимое файлов для передачи в LLM.
"""

import os

from core.ignore import is_ignored_path, load_ignore_rules

# Каталоги, которые пропускаем
SKIP_DIRS = {
    ".git",
    "__pycache__",
    "node_modules",
    ".venv",
    "venv",
    "env",
    "dist",
    "build",
    ".next",
    ".nuxt",
    ".idea",
    ".vscode",
    "coverage",
    ".pytest_cache",
    ".mypy_cache",
    ".tox",
    ".eggs",
    ".sass-cache",
    ".cache",
    "logs",
    "~",
}

# Файлы по имени (без расширения или особые имена)
KNOWN_FILES = {
    "Dockerfile",
    "Makefile",
    "Rakefile",
    "Gemfile",
    "Procfile",
    "Vagrantfile",
    ".gitignore",
    ".dockerignore",
    ".env.example",
    "requirements.txt",
    "setup.py",
    "setup.cfg",
    "pyproject.toml",
    "package.json",
    "tsconfig.json",
    "README.md",
    "main.py",
    "app.py",
    "index.js",
    "index.ts",
    "index.html",
}

# Файлы, которые всегда пропускаем
SKIP_FILES = {
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "poetry.lock",
    "Pipfile.lock",
    "composer.lock",
    ".env",
    ".env.local",
    ".env.production",
    ".env.development",
    "id_rsa",
    "id_ed25519",
    ".DS_Store",
    "Thumbs.db",
}

MAX_FILE_SIZE = 12_000
MAX_TOTAL_SIZE = 32_000
MAX_INSTRUCTIONS_SIZE = 12_000
MAX_TOP_LEVEL_ENTRIES = 120


def get_project_instructions(project_root: str) -> str:
    """Load trusted, bounded repository guidance for the agent."""
    path = os.path.join(project_root, ".citadex.md")
    try:
        with open(path, encoding="utf-8") as stream:
            return stream.read(MAX_INSTRUCTIONS_SIZE).strip()
    except OSError:
        return "— no project-specific instructions —"


def _should_read(fname):
    """Read only high-signal entry points; tools load other files on demand."""
    return fname not in SKIP_FILES and fname in KNOWN_FILES


def get_project_context(project_root):
    """
    Return a bounded top-level snapshot.

    Deeper project exploration is deliberately delegated to agent tools so
    launching Citadex from a broad directory never walks an entire drive.
    """
    project_root = os.path.normpath(os.path.abspath(project_root))

    if not os.path.isdir(project_root):
        return f"Project directory not found: {project_root}"

    tree_lines: list[str] = []
    file_sections: list[str] = []
    total_size = 0
    ignore_rules = load_ignore_rules(project_root)
    try:
        with os.scandir(project_root) as scanner:
            entries = sorted(scanner, key=lambda entry: entry.name.casefold())
    except OSError:
        entries = []

    visible = []
    for entry in entries:
        name = entry.name
        path = entry.path
        if name in SKIP_FILES or name in SKIP_DIRS or name.startswith("."):
            continue
        if is_ignored_path(path, project_root, ignore_rules):
            continue
        visible.append(entry)

    for entry in visible[:MAX_TOP_LEVEL_ENTRIES]:
        try:
            is_directory = entry.is_dir(follow_symlinks=False)
        except OSError:
            is_directory = False
        tree_lines.append(f"  {entry.name}/" if is_directory else f"  {entry.name}")
        if is_directory or not _should_read(entry.name):
            continue
        try:
            fsize = entry.stat(follow_symlinks=False).st_size
        except OSError:
            continue
        if fsize == 0 or fsize > MAX_FILE_SIZE or total_size + fsize > MAX_TOTAL_SIZE:
            continue
        try:
            with open(entry.path, encoding="utf-8", errors="ignore") as stream:
                content = stream.read(MAX_FILE_SIZE)
        except OSError:
            continue
        file_sections.append(f"--- {entry.name} ---\n{content}")
        total_size += len(content)

    if len(visible) > MAX_TOP_LEVEL_ENTRIES:
        tree_lines.append(f"  … {len(visible) - MAX_TOP_LEVEL_ENTRIES} more top-level entries")

    # Собираем контекст
    from core.project_environment import detect_project_environment

    parts = [
        detect_project_environment(project_root).render(),
        "",
        f"Project: {project_root}",
        "",
        "File tree:",
        *tree_lines,
    ]

    if file_sections:
        parts.append("")
        parts.append("File contents:")
        parts.extend(file_sections)

    return "\n".join(parts)


def get_git_log(project_root: str) -> str:
    """Run ``git log --oneline -15`` in project_root and return the output.

    Returns an empty string if the directory is not a git repository or if
    git is not installed, so callers can safely embed the result in prompts.
    """
    import subprocess

    try:
        result = subprocess.run(
            ["git", "log", "--oneline", "-15"],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
        return ""
    except Exception:
        return ""
