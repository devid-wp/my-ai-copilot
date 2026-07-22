from core.context_manager import get_project_instructions


def test_loads_citadex_project_instructions(tmp_path):
    (tmp_path / ".citadex.md").write_text("- Use Python 3.12\n- Run pytest", encoding="utf-8")
    assert "Python 3.12" in get_project_instructions(str(tmp_path))


def test_missing_instructions_have_safe_default(tmp_path):
    assert "no project-specific" in get_project_instructions(str(tmp_path))
