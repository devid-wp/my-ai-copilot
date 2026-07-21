from core.agent_loop import AgentLoopGuard, pseudo_tool_name
from core.tools import AgentLimits, ToolCall, ToolError, ToolResult, ToolStatus


def call(path="file.py"):
    return ToolCall(id="call_1", name="read_file", arguments={"path": path})


def result(tool_call, status=ToolStatus.SUCCESS):
    error = None if status is ToolStatus.SUCCESS else ToolError(code="FAILED", message="failed")
    return ToolResult(
        call_id=tool_call.id,
        name=tool_call.name,
        status=status,
        error=error,
    )


def test_guard_blocks_call_after_repeat_limit():
    guard = AgentLoopGuard(AgentLimits(max_repeated_calls=2))
    tool_call = call()

    assert guard.inspect(tool_call) is None
    assert guard.inspect(tool_call) is None
    error = guard.inspect(tool_call)

    assert error is not None
    assert error.code == "REPEATED_TOOL_CALL"


def test_guard_enforces_total_tool_call_limit():
    guard = AgentLoopGuard(AgentLimits(max_tool_calls=1))

    assert guard.inspect(call("one.py")) is None
    error = guard.inspect(call("two.py"))

    assert error is not None
    assert error.code == "TOOL_CALL_LIMIT"


def test_consecutive_error_limit_resets_after_success():
    guard = AgentLoopGuard(AgentLimits(max_consecutive_errors=2))
    tool_call = call()

    guard.record(tool_call, result(tool_call, ToolStatus.ERROR))
    assert guard.error_limit_reached is False
    guard.record(tool_call, result(tool_call))
    assert guard.consecutive_errors == 0


def test_pseudo_tool_call_is_detected_but_regular_json_is_not():
    response = '```json\n{"name":"create_file","arguments":{"path":"index.html"}}\n```'

    assert pseudo_tool_name(response) == "create_file"
    assert pseudo_tool_name('```json {"name":"read_file","arguments":{"path":"a.py"}} ```') == (
        "read_file"
    )
    assert pseudo_tool_name('{"status":"ok"}') is None
    assert pseudo_tool_name("Use create_file to continue") is None
