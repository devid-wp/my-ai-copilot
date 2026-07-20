from core.tools import (
    PermissionMode,
    PermissionPolicy,
    ToolCall,
    ToolDefinition,
    ToolRegistry,
    ToolRisk,
    ToolStatus,
)


def definition(risk: ToolRisk) -> ToolDefinition:
    return ToolDefinition(
        name="sample_tool",
        description="A test tool.",
        input_schema={
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
        },
        risk=risk,
    )


def execute_with_policy(risk, mode, callback=None):
    calls = []
    registry = ToolRegistry(PermissionPolicy(mode), callback)
    registry.register(definition(risk), lambda args: calls.append(args) or {"status": "done"})
    result = registry.execute(
        ToolCall(id="call_1", name="sample_tool", arguments={"path": "src/app.py"})
    )
    return result, calls


def test_read_only_tool_does_not_request_approval():
    requests = []
    result, calls = execute_with_policy(
        ToolRisk.READ_ONLY,
        PermissionMode.ASK,
        lambda request: requests.append(request) or False,
    )

    assert result.status is ToolStatus.SUCCESS
    assert len(calls) == 1
    assert requests == []


def test_ask_mode_executes_write_only_after_approval():
    requests = []
    result, calls = execute_with_policy(
        ToolRisk.PROJECT_WRITE,
        PermissionMode.ASK,
        lambda request: requests.append(request) or True,
    )

    assert result.status is ToolStatus.SUCCESS
    assert len(calls) == 1
    assert requests[0].risk is ToolRisk.PROJECT_WRITE
    assert requests[0].detail == "src/app.py"


def test_denied_call_never_reaches_handler():
    result, calls = execute_with_policy(
        ToolRisk.PROJECT_DELETE,
        PermissionMode.ASK,
        lambda _request: False,
    )

    assert result.status is ToolStatus.DENIED
    assert result.error is not None
    assert result.error.code == "PERMISSION_DENIED"
    assert result.error.details["risk"] == "project_delete"
    assert calls == []


def test_auto_mode_allows_risky_tool_without_callback():
    result, calls = execute_with_policy(ToolRisk.COMMAND_WRITE, PermissionMode.AUTO)

    assert result.status is ToolStatus.SUCCESS
    assert len(calls) == 1


def test_read_only_mode_denies_mutations_but_allows_reads():
    denied, denied_calls = execute_with_policy(ToolRisk.PROJECT_WRITE, PermissionMode.READ_ONLY)
    allowed, allowed_calls = execute_with_policy(ToolRisk.READ_ONLY, PermissionMode.READ_ONLY)

    assert denied.status is ToolStatus.DENIED
    assert denied_calls == []
    assert allowed.status is ToolStatus.SUCCESS
    assert len(allowed_calls) == 1
