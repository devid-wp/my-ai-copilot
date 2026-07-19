import pytest

from core.tools import (
    AgentLimits,
    ProviderCapabilities,
    ToolCall,
    ToolDefinition,
    ToolError,
    ToolResult,
    ToolRisk,
    ToolStatus,
)


def test_tool_call_requires_id_and_name():
    with pytest.raises(ValueError, match="id"):
        ToolCall(id="", name="read_file", arguments={})
    with pytest.raises(ValueError, match="name"):
        ToolCall(id="call_1", name="", arguments={})


def test_definition_builds_openai_schema():
    definition = ToolDefinition(
        name="read_file",
        description="Read a project file.",
        input_schema={
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
        },
        risk=ToolRisk.READ_ONLY,
    )

    schema = definition.to_openai_schema()

    assert schema["type"] == "function"
    assert schema["function"]["name"] == "read_file"
    assert schema["function"]["parameters"]["required"] == ["path"]


def test_result_invariants():
    error = ToolError(code="NOT_FOUND", message="Missing file")
    result = ToolResult(
        call_id="call_1",
        name="read_file",
        status=ToolStatus.ERROR,
        error=error,
        duration_ms=5,
    )
    assert result.error == error

    with pytest.raises(ValueError, match="must contain ToolError"):
        ToolResult(call_id="call_2", name="read_file", status=ToolStatus.ERROR)


def test_agent_limits_must_be_positive():
    assert AgentLimits().max_steps == 30
    with pytest.raises(ValueError, match="max_steps"):
        AgentLimits(max_steps=0)


def test_provider_capability_defaults_are_safe():
    capabilities = ProviderCapabilities()
    assert capabilities.native_tools is False
    assert capabilities.parallel_tools is False
    assert capabilities.streaming_tools is False
