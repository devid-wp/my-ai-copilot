from core.project_environment import detect_project_environment


def test_detects_python_project_commands_and_config(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname="demo"\ndependencies=["fastapi"]\n', encoding="utf-8"
    )
    environment = detect_project_environment(str(tmp_path))
    assert environment.languages == ("Python",)
    assert environment.frameworks == ("FastAPI",)
    assert environment.test_commands == ("pytest",)
    assert "pyproject.toml" in environment.config_files
