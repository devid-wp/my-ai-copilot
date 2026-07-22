from core.verification import relevant_test_scope, verify_agent_changes


def test_verification_rejects_invalid_python(tmp_path):
    (tmp_path / "bad.py").write_text("def broken(:", encoding="utf-8")
    result = verify_agent_changes(["bad.py"], str(tmp_path))
    assert result["ok"] is False
    assert result["errors"]


def test_verification_rereads_valid_file(tmp_path):
    (tmp_path / "ok.py").write_text("value = 1\n", encoding="utf-8")
    result = verify_agent_changes(["ok.py"], str(tmp_path))
    assert result["ok"] is True
    assert result["files"] == [str(tmp_path / "ok.py")]


def test_relevant_test_scope_maps_python_module_to_test(tmp_path):
    (tmp_path / "core").mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / "core" / "router.py").write_text("", encoding="utf-8")
    (tmp_path / "tests" / "test_router.py").write_text("", encoding="utf-8")
    assert relevant_test_scope(["core/router.py"], str(tmp_path)) == "tests/test_router.py"
