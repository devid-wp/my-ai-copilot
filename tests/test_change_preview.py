from core.agent_executor import preview_file_change


def test_preview_shows_removed_and_added_lines(tmp_path):
    (tmp_path / "index.html").write_text("<h1>Добро пожаловать</h1>\n", encoding="utf-8")
    preview = preview_file_change(
        "create_file", {"path": "index.html", "content": "<h1>Hello</h1>\n"}, str(tmp_path)
    )
    assert "-<h1>Добро пожаловать</h1>" in preview
    assert "+<h1>Hello</h1>" in preview
