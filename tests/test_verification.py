from core.verification import verify_agent_changes


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
