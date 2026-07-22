import pytest

from core.agent_executor import read_file
from core.ignore import is_ignored_path, load_ignore_rules


def test_defaults_and_custom_rules_are_applied(tmp_path):
    (tmp_path / ".citadexignore").write_text("private/**\n*.secret\n", encoding="utf-8")
    rules = load_ignore_rules(str(tmp_path))
    assert is_ignored_path(tmp_path / "node_modules" / "x.js", str(tmp_path), rules)
    assert is_ignored_path(tmp_path / "token.key", str(tmp_path), rules)
    assert is_ignored_path(tmp_path / "private" / "data.txt", str(tmp_path), rules)


def test_read_file_refuses_ignored_secret(tmp_path):
    (tmp_path / ".env").write_text("SECRET=value", encoding="utf-8")
    with pytest.raises(PermissionError, match="citadexignore"):
        read_file({"path": ".env"}, str(tmp_path))
