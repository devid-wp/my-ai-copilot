from core.agent_executor import copy_file, file_exists, get_file_info, move_file


def test_file_management_tools(tmp_path):
    (tmp_path / "a.txt").write_text("hello", encoding="utf-8")
    copied = copy_file({"source": "a.txt", "destination": "b.txt"}, str(tmp_path))
    assert copied["status"] == "copied"
    assert get_file_info({"path": "b.txt"}, str(tmp_path))["size"] == 5
    move_file({"source": "b.txt", "destination": "c.txt"}, str(tmp_path))
    assert file_exists({"path": "b.txt"}, str(tmp_path))["exists"] is False
    assert file_exists({"path": "c.txt"}, str(tmp_path))["exists"] is True
