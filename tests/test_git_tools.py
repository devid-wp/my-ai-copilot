from core.agent_executor import git_diff, git_status


def test_git_tools_return_structured_result(tmp_path, monkeypatch):
    class Result:
        returncode = 0
        stdout = "## main\n"
        stderr = ""

    monkeypatch.setattr("core.agent_executor.subprocess.run", lambda *args, **kwargs: Result())
    assert git_status({}, str(tmp_path))["returncode"] == 0
    assert git_diff({}, str(tmp_path))["status"] == "completed"
