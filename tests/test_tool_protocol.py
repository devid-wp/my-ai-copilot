from core.llm_client import TOOLS as NVIDIA_TOOLS
from core.ollama_client import TOOLS as OLLAMA_TOOLS
from core.tool_protocol import normalize_tool_call


def test_all_providers_receive_identical_tool_schemas():
    assert NVIDIA_TOOLS == OLLAMA_TOOLS
    assert {item["function"]["name"] for item in NVIDIA_TOOLS} >= {"move_file", "run_tests"}


def test_normalizes_string_arguments():
    call = normalize_tool_call({"id": "1", "function": {"name": "read_file", "arguments": '{"path":"a.py"}'}})
    assert call.arguments == {"path": "a.py"}
