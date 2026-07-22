from core.agent_executor import copy_file, create_tool_registry, file_exists, get_file_info, move_file
from core.tools import ToolCall, ToolStatus


def test_file_management_tools(tmp_path):
    (tmp_path / "a.txt").write_text("hello", encoding="utf-8")
    copied = copy_file({"source": "a.txt", "destination": "b.txt"}, str(tmp_path))
    assert copied["status"] == "copied"
    assert get_file_info({"path": "b.txt"}, str(tmp_path))["size"] == 5
    move_file({"source": "b.txt", "destination": "c.txt"}, str(tmp_path))
    assert file_exists({"path": "b.txt"}, str(tmp_path))["exists"] is False
    assert file_exists({"path": "c.txt"}, str(tmp_path))["exists"] is True


def test_move_directory_to_approved_external_path_and_remember_permission(tmp_path):
    project = tmp_path / "project"
    source = project / "source-folder"
    source.mkdir(parents=True)
    (source / "data.txt").write_text("hello", encoding="utf-8")
    external = tmp_path / "external-folder"
    approvals: list[str] = []
    remembered: set[str] = set()

    registry = create_tool_registry(
        str(project),
        auto_approve=True,
        approve_external=lambda path: approvals.append(path) or True,
        approved_external_paths=remembered,
    )
    result = registry.execute(
        ToolCall(
            id="move-directory",
            name="move_file",
            arguments={"source": "source-folder", "destination": str(external)},
        )
    )

    assert result.status is ToolStatus.SUCCESS
    assert (external / "data.txt").read_text(encoding="utf-8") == "hello"
    assert not source.exists()
    assert approvals == [str(external)]
    assert str(external) in remembered

    second_registry = create_tool_registry(
        str(project),
        auto_approve=True,
        approve_external=lambda _path: False,
        approved_external_paths=remembered,
    )
    info = second_registry.execute(
        ToolCall(
            id="external-info",
            name="get_file_info",
            arguments={"path": str(external / "data.txt")},
        )
    )
    assert info.status is ToolStatus.SUCCESS
