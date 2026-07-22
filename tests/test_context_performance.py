from core.context_manager import get_project_context


def test_initial_context_keeps_tree_but_skips_bulk_source_contents(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[project]\nname='demo'", encoding="utf-8")
    (tmp_path / "main.py").write_text("print('entry')", encoding="utf-8")
    (tmp_path / "large_module.py").write_text("SECRET_MARKER = 1", encoding="utf-8")
    context = get_project_context(str(tmp_path))
    assert "large_module.py" in context
    assert "SECRET_MARKER" not in context
    assert "print('entry')" in context
    assert "name='demo'" in context
