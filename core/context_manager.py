# core/context_manager.py
"""
Сканер проекта.
Читает структуру каталогов и содержимое файлов для передачи в LLM.
"""

import os

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

# Расширения файлов, которые читаем
CODE_EXTENSIONS = {
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".mjs",
    ".cjs",
    ".html",
    ".css",
    ".scss",
    ".less",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".cfg",
    ".ini",
    ".md",
    ".txt",
    ".rst",
    ".sh",
    ".bat",
    ".ps1",
    ".cmd",
    ".sql",
    ".graphql",
    ".xml",
    ".svg",
    ".c",
    ".cpp",
    ".h",
    ".hpp",
    ".cs",
    ".java",
    ".go",
    ".rs",
    ".rb",
    ".php",
    ".lua",
    ".r",
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

MAX_FILE_SIZE = 15_000  # 15 KB на файл
MAX_TOTAL_SIZE = 80_000  # 80 KB общий лимит контекста


def _should_read(fname):
    """Проверяет, нужно ли читать файл."""
    if fname in SKIP_FILES:
        return False
    if fname in KNOWN_FILES:
        return True
    _, ext = os.path.splitext(fname)
    return ext.lower() in CODE_EXTENSIONS


def get_project_context(project_root):
    """
    Сканирует каталог проекта и возвращает отформатированный
    контекст для LLM: дерево файлов + содержимое.
    """
    project_root = os.path.normpath(os.path.abspath(project_root))

    if not os.path.isdir(project_root):
        return f"Project directory not found: {project_root}"

    tree_lines = []
    file_sections = []
    total_size = 0

    for root, dirs, files in os.walk(project_root):
        # Фильтруем каталоги — пропускаем скрытые и ненужные
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS and not d.startswith("."))

        rel_root = os.path.relpath(root, project_root)
        if rel_root == ".":
            rel_root = ""

        depth = 0 if not rel_root else rel_root.count(os.sep) + 1
        indent = "  " * depth

        if rel_root:
            tree_lines.append(f"{indent}{os.path.basename(root)}/")

        for fname in sorted(files):
            if fname in SKIP_FILES:
                continue

            file_indent = "  " * (depth + 1)
            tree_lines.append(f"{file_indent}{fname}")

            # Читаем только подходящие файлы
            if not _should_read(fname):
                continue

            full_path = os.path.join(root, fname)

            try:
                fsize = os.path.getsize(full_path)
            except OSError:
                continue

            if fsize > MAX_FILE_SIZE or fsize == 0:
                continue

            if total_size + fsize > MAX_TOTAL_SIZE:
                continue

            try:
                with open(full_path, encoding="utf-8", errors="ignore") as f:
                    content = f.read()
            except OSError:
                continue

            rel_path = os.path.join(rel_root, fname) if rel_root else fname
            rel_path = rel_path.replace(os.sep, "/")

            file_sections.append(f"--- {rel_path} ---\n{content}")
            total_size += len(content)

    # Собираем контекст
    parts = [
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
