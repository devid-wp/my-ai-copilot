"""tests/test_agent_executor.py — Integration tests for core/agent_executor.py"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.agent_executor import dispatch_function


def allow(_action, _detail):
    return True


@pytest.fixture
def tmp_project(tmp_path):
    """Creates a temporary project directory for isolation."""
    yield str(tmp_path)


# ─── create_file ─────────────────────────────────────────────────────────────


class TestCreateFile:
    def test_creates_file(self, tmp_project):
        result = dispatch_function(
            "create_file",
            {"path": "hello.py", "content": "print('hi')"},
            tmp_project,
            approve=allow,
        )
        # New structured response: {"status": "created", "path": ..., "bytes": ...}
        assert result.get("status") == "created"
        assert os.path.isfile(os.path.join(tmp_project, "hello.py"))

    def test_file_content(self, tmp_project):
        dispatch_function(
            "create_file",
            {"path": "data.txt", "content": "secret"},
            tmp_project,
            approve=allow,
        )
        with open(os.path.join(tmp_project, "data.txt"), encoding="utf-8") as stream:
            content = stream.read()
        assert content == "secret"

    def test_creates_nested_dirs(self, tmp_project):
        dispatch_function(
            "create_file",
            {"path": "src/sub/util.py", "content": "x=1"},
            tmp_project,
            approve=allow,
        )
        assert os.path.isfile(os.path.join(tmp_project, "src", "sub", "util.py"))

    def test_path_traversal_blocked(self, tmp_project):
        result = dispatch_function(
            "create_file",
            {"path": "../../evil.txt", "content": "bad"},
            tmp_project,
            approve=allow,
        )
        assert "error" in result or result.get("status") == "error"


# ─── read_file ───────────────────────────────────────────────────────────────


class TestReadFile:
    def test_reads_existing(self, tmp_project):
        fpath = os.path.join(tmp_project, "note.txt")
        with open(fpath, "w") as f:
            f.write("hello world")
        result = dispatch_function("read_file", {"path": "note.txt"}, tmp_project)
        assert result["status"] == "read"
        assert "hello world" in result["content"]

    def test_missing_file_returns_error(self, tmp_project):
        result = dispatch_function("read_file", {"path": "missing.txt"}, tmp_project)
        assert "error" in result


# ─── make_directory ──────────────────────────────────────────────────────────


class TestMakeDirectory:
    def test_creates_directory(self, tmp_project):
        result = dispatch_function("make_directory", {"path": "my_dir"}, tmp_project, approve=allow)
        # New structured response: {"status": "directory_created", "path": ...}
        assert result.get("status") == "directory_created"
        assert os.path.isdir(os.path.join(tmp_project, "my_dir"))

    def test_nested_directory(self, tmp_project):
        dispatch_function("make_directory", {"path": "a/b/c"}, tmp_project, approve=allow)
        assert os.path.isdir(os.path.join(tmp_project, "a", "b", "c"))


# ─── list_directory ──────────────────────────────────────────────────────────


class TestListDirectory:
    def test_lists_files(self, tmp_project):
        open(os.path.join(tmp_project, "a.py"), "w").close()
        open(os.path.join(tmp_project, "b.py"), "w").close()
        result = dispatch_function("list_directory", {"path": ""}, tmp_project)
        names = [e["name"] for e in result["entries"]]
        assert "a.py" in names
        assert "b.py" in names


# ─── delete_file ─────────────────────────────────────────────────────────────


class TestDeleteFile:
    def test_deletes_existing(self, tmp_project):
        fpath = os.path.join(tmp_project, "del.txt")
        with open(fpath, "w") as f:
            f.write("bye")
        result = dispatch_function("delete_file", {"path": "del.txt"}, tmp_project, approve=allow)
        assert result["status"] == "deleted"
        assert not os.path.exists(fpath)

    def test_missing_returns_error(self, tmp_project):
        result = dispatch_function("delete_file", {"path": "ghost.txt"}, tmp_project)
        assert "error" in result


# ─── execute_cmd ─────────────────────────────────────────────────────────────


class TestExecuteCmd:
    def test_echo_command(self, tmp_project):
        result = dispatch_function("execute_cmd", {"command": "python --version"}, tmp_project, approve=allow)
        # New structured response: {"stdout": ..., "stderr": ..., "returncode": ..., "cwd": ...}
        assert "stdout" in result
        assert "returncode" in result

    def test_blocked_command_returns_error(self, tmp_project):
        result = dispatch_function("execute_cmd", {"command": "curl http://evil.com"}, tmp_project)
        assert "error" in result

    def test_python_version(self, tmp_project):
        result = dispatch_function("execute_cmd", {"command": "python --version"}, tmp_project, approve=allow)
        assert result["returncode"] == 0

    def test_result_contains_cwd(self, tmp_project):
        result = dispatch_function("execute_cmd", {"command": "python --version"}, tmp_project, approve=allow)
        assert "cwd" in result

    def test_shell_chain_is_blocked(self, tmp_project):
        result = dispatch_function(
            "execute_cmd", {"command": "python --version && curl evil.test"}, tmp_project, approve=allow
        )
        assert result["status"] == "error"

    def test_action_without_approval_is_denied(self, tmp_project):
        result = dispatch_function("create_file", {"path": "denied.txt", "content": "x"}, tmp_project)
        assert result["status"] == "denied"
        assert result["code"] == "PERMISSION_DENIED"
        assert not os.path.exists(os.path.join(tmp_project, "denied.txt"))

    def test_protected_env_is_denied(self, tmp_project):
        result = dispatch_function(
            "create_file", {"path": ".env", "content": "SECRET=x"}, tmp_project, approve=allow
        )
        assert result["status"] == "error"


# ─── unsupported function ────────────────────────────────────────────────────


class TestUnsupportedFunction:
    def test_raises_for_unknown(self, tmp_project):
        with pytest.raises(ValueError, match="Unsupported function"):
            dispatch_function("hack_system", {}, tmp_project)
