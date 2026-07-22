from pathlib import Path

from core.agent_executor import create_file
from core.undo import undo_last_action


def test_undo_restores_previous_file_content(tmp_path):
    target = tmp_path / "note.txt"
    target.write_text("before", encoding="utf-8")
    create_file({"path": "note.txt", "content": "after"}, str(tmp_path))
    result = undo_last_action(str(tmp_path))
    assert result["status"] == "restored"
    assert target.read_text(encoding="utf-8") == "before"


def test_undo_removes_new_file(tmp_path):
    create_file({"path": "new.txt", "content": "new"}, str(tmp_path))
    undo_last_action(str(tmp_path))
    assert not Path(tmp_path / "new.txt").exists()
