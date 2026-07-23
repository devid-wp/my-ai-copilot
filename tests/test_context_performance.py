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


def test_initial_context_never_walks_nested_directories(tmp_path):
    nested = tmp_path / "large-tree"
    nested.mkdir()
    for index in range(500):
        (nested / f"file-{index}.txt").write_text("SHOULD_NOT_BE_SCANNED", encoding="utf-8")

    context = get_project_context(str(tmp_path))

    assert "large-tree/" in context
    assert "file-499.txt" not in context
    assert "SHOULD_NOT_BE_SCANNED" not in context


def test_initial_context_caps_top_level_entries(tmp_path):
    for index in range(150):
        (tmp_path / f"item-{index:03}.txt").write_text("x", encoding="utf-8")

    context = get_project_context(str(tmp_path))

    assert "30 more top-level entries" in context
    assert "item-149.txt" not in context
