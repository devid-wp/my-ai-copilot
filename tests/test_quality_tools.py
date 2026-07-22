from core.agent_executor import format_code, run_tests


def test_python_quality_tools_choose_safe_commands(tmp_path, monkeypatch):
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'", encoding="utf-8")
    (tmp_path / "x.py").write_text("x=1", encoding="utf-8")
    commands = []

    def execute(args, _root):
        commands.append(args["command"])
        return {"returncode": 0}

    monkeypatch.setattr("core.agent_executor.execute_cmd", execute)
    assert run_tests({}, str(tmp_path))["returncode"] == 0
    assert format_code({"path": "x.py"}, str(tmp_path))["returncode"] == 0
    assert commands == ["pytest", "python -m ruff format x.py"]
