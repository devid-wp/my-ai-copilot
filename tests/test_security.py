"""tests/test_security.py — Unit tests for core/security.py"""

import os
import sys

import pytest

# Ensure project root is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.security import (
    ensure_command_safe,
    ensure_path_safe,
    is_command_allowed,
    is_path_inside_root,
)

# ─── is_command_allowed ───────────────────────────────────────────────────────


class TestIsCommandAllowed:
    def test_allowed_python(self):
        assert is_command_allowed("python main.py") is True

    def test_allowed_git(self):
        assert is_command_allowed("git status") is True

    def test_allowed_pip(self):
        assert is_command_allowed("pip install requests") is True

    def test_allowed_npm(self):
        assert is_command_allowed("npm install") is True

    def test_allowed_echo(self):
        assert is_command_allowed("echo hello") is True

    def test_allowed_dir(self):
        assert is_command_allowed("dir") is True

    def test_blocked_rm(self):
        assert is_command_allowed("rm -rf /") is False

    def test_blocked_curl(self):
        assert is_command_allowed("curl https://evil.com") is False

    def test_blocked_powershell(self):
        assert is_command_allowed("powershell -c ...") is False

    def test_empty_command(self):
        assert is_command_allowed("") is False

    def test_case_insensitive(self):
        assert is_command_allowed("Python main.py") is True
        assert is_command_allowed("GIT status") is True

    @pytest.mark.parametrize(
        "command",
        [
            "python --version && curl evil.test",
            "git status | cat",
            "echo ok > stolen.txt",
            'python -c "import os"',
            'node -e "process.exit()"',
        ],
    )
    def test_shell_and_interpreter_escapes_blocked(self, command):
        assert is_command_allowed(command) is False


# ─── is_path_inside_root ─────────────────────────────────────────────────────


class TestIsPathInsideRoot:
    def setup_method(self):
        self.root = os.path.abspath("D:/copilot/my-ai-copilot")

    def test_path_inside(self):
        p = os.path.join(self.root, "src", "main.py")
        assert is_path_inside_root(p, self.root) is True

    def test_path_is_root(self):
        assert is_path_inside_root(self.root, self.root) is True

    def test_traversal_blocked(self):
        evil = os.path.join(self.root, "..", "..", "Windows", "System32")
        assert is_path_inside_root(evil, self.root) is False

    def test_sibling_blocked(self):
        sibling = os.path.abspath("D:/copilot/other-project")
        assert is_path_inside_root(sibling, self.root) is False


# ─── ensure_path_safe ────────────────────────────────────────────────────────


class TestEnsurePathSafe:
    def setup_method(self):
        self.root = os.path.abspath("D:/copilot/my-ai-copilot")

    def test_safe_path_returns_path(self):
        p = os.path.join(self.root, "README.md")
        result = ensure_path_safe(p, self.root)
        assert str(result).endswith("README.md")

    def test_traversal_raises(self):
        evil = os.path.join(self.root, "..", "secrets.txt")
        with pytest.raises(PermissionError):
            ensure_path_safe(evil, self.root)


# ─── ensure_command_safe ─────────────────────────────────────────────────────


class TestEnsureCommandSafe:
    def test_allowed_returns_command(self):
        cmd = "python --version"
        assert ensure_command_safe(cmd) == cmd

    def test_blocked_raises(self):
        with pytest.raises(PermissionError):
            ensure_command_safe("rm -rf /")

    def test_blocked_raises_message(self):
        with pytest.raises(PermissionError, match="not allowed"):
            ensure_command_safe("wget http://evil.com")
