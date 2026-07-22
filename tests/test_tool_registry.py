import pytest

from core.agent_executor import create_tool_registry
from core.tools import ToolCall, ToolDefinition, ToolRegistry, ToolRisk, ToolStatus


@pytest.fixture
def definition():
    return ToolDefinition(
        name="echo",
        description="Return the supplied text.",
        input_schema={
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
        },
        risk=ToolRisk.READ_ONLY,
    )


def test_registry_preserves_registration_order_and_builds_schemas(definition):
    registry = ToolRegistry()
    registry.register(definition, lambda args: args)

    assert registry.get("echo") == definition
    assert registry.definitions() == (definition,)
    assert registry.openai_schemas()[0]["function"]["name"] == "echo"


def test_registry_rejects_duplicate_names(definition):
    registry = ToolRegistry()
    registry.register(definition, lambda args: args)

    with pytest.raises(ValueError, match="already registered"):
        registry.register(definition, lambda args: args)


def test_registry_rejects_invalid_definition_schema():
    definition = ToolDefinition(
        name="broken",
        description="Broken schema.",
        input_schema={"type": "object", "required": "path"},
        risk=ToolRisk.READ_ONLY,
    )

    with pytest.raises(ValueError, match="Invalid JSON Schema"):
        ToolRegistry().register(definition, lambda args: args)


def test_registry_executes_tool_without_mutating_call_arguments(definition):
    registry = ToolRegistry()

    def handler(args):
        args["handled"] = True
        return args

    registry.register(definition, handler)
    call = ToolCall(id="call_1", name="echo", arguments={"text": "hello"})

    result = registry.execute(call)

    assert result.status is ToolStatus.SUCCESS
    assert result.content == {"text": "hello", "handled": True}
    assert call.arguments == {"text": "hello"}


def test_registry_returns_structured_unknown_tool_error():
    result = ToolRegistry().execute(ToolCall(id="call_2", name="missing", arguments={}))

    assert result.status is ToolStatus.ERROR
    assert result.error is not None
    assert result.error.code == "UNKNOWN_TOOL"


def test_outside_project_permission_error_has_actionable_code():
    registry = ToolRegistry()
    definition = ToolDefinition(
        name="write",
        description="Write a file.",
        input_schema={"type": "object"},
        risk=ToolRisk.PROJECT_WRITE,
    )

    def outside(_args):
        raise PermissionError("Path 'outside.txt' is outside project root 'project'.")

    registry.register(definition, outside)
    result = registry.execute(ToolCall(id="call_outside", name="write", arguments={}))

    assert result.error is not None
    assert result.error.code == "PATH_OUTSIDE_PROJECT"


def test_registry_rejects_missing_required_argument_before_handler(definition):
    calls: list[dict] = []
    registry = ToolRegistry()
    registry.register(definition, lambda args: calls.append(args) or args)

    result = registry.execute(ToolCall(id="call_invalid", name="echo", arguments={}))

    assert result.status is ToolStatus.ERROR
    assert result.error is not None
    assert result.error.code == "INVALID_ARGUMENTS"
    assert result.error.details["path"] == "$"
    assert calls == []


def test_registry_reports_nested_validation_path():
    definition = ToolDefinition(
        name="patch",
        description="Apply a patch.",
        input_schema={
            "type": "object",
            "properties": {
                "patches": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {"line": {"type": "integer"}},
                        "required": ["line"],
                    },
                }
            },
            "required": ["patches"],
        },
        risk=ToolRisk.PROJECT_WRITE,
    )
    registry = ToolRegistry()
    registry.register(definition, lambda args: args)

    result = registry.execute(
        ToolCall(id="call_nested", name="patch", arguments={"patches": [{"line": "one"}]})
    )

    assert result.error is not None
    assert result.error.code == "INVALID_ARGUMENTS"
    assert result.error.details["path"] == "$.patches.0.line"


def test_registry_converts_handler_exception_to_error(definition):
    registry = ToolRegistry()

    def fail(_args):
        raise FileNotFoundError("missing.txt")

    registry.register(definition, fail)
    result = registry.execute(ToolCall(id="call_3", name="echo", arguments={"text": "x"}))

    assert result.status is ToolStatus.ERROR
    assert result.error is not None
    assert result.error.code == "TOOL_EXECUTION_FAILED"
    assert result.error.details == {"exception_type": "FileNotFoundError"}


def test_registry_rejects_non_mapping_handler_result(definition):
    registry = ToolRegistry()
    registry.register(definition, lambda _args: "wrong")  # type: ignore[arg-type,return-value]

    result = registry.execute(ToolCall(id="call_4", name="echo", arguments={"text": "x"}))

    assert result.status is ToolStatus.ERROR
    assert result.error is not None
    assert result.error.details["exception_type"] == "TypeError"


def test_builtin_registry_contains_every_runtime_tool(tmp_path):
    registry = create_tool_registry(str(tmp_path))

    assert {definition.name for definition in registry.definitions()} == {
        "create_file",
        "edit_file",
        "delete_file",
        "make_directory",
        "execute_cmd",
        "list_directory",
        "read_file",
        "search_in_files",
        "move_file",
        "copy_file",
        "file_exists",
        "get_file_info",
        "git_status",
        "git_diff",
        "run_tests",
        "format_code",
    }


def test_builtin_registry_executes_bound_read_tool(tmp_path):
    (tmp_path / "hello.txt").write_text("hello", encoding="utf-8")
    registry = create_tool_registry(str(tmp_path))

    result = registry.execute(ToolCall(id="call_read", name="read_file", arguments={"path": "hello.txt"}))

    assert result.status is ToolStatus.SUCCESS
    assert result.content["content"] == "hello"
