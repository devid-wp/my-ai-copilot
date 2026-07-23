"""Live provider smoke test for native tool calling."""

from __future__ import annotations

from tempfile import TemporaryDirectory
from typing import Any

from core.agent_executor import create_tool_registry
from core.security import close_project_logger
from core.tool_protocol import normalize_tool_call
from core.tools import ToolCall, ToolStatus

SMOKE_PATH = "pyproject.toml"
E2E_PATH = "citadex-smoke/probe.txt"
E2E_CONTENT = "CITADEX_SMOKE_OK"


def check_native_tool_calling(client: Any) -> str:
    """Ask the provider for a harmless tool call and return its tool name."""
    messages = [
        {
            "role": "system",
            "content": "You are testing native function calling. Never answer with pseudo-JSON.",
        },
        {
            "role": "user",
            "content": (
                "Проверь наличие файла pyproject.toml. Обязательно вызови native tool "
                "file_exists с path=pyproject.toml. Не отвечай текстом."
            ),
        },
    ]
    list(client.ask_stream("", messages=messages))
    raw_calls = client.get_last_tool_calls()
    if not raw_calls:
        raise RuntimeError("Модель не выполнила native tool call.")
    call = normalize_tool_call(raw_calls[0], "smoke_call")
    if call.name != "file_exists" or call.arguments.get("path") != SMOKE_PATH:
        raise RuntimeError(f"Получен неожиданный tool call: {call.name}.")
    return call.name


def _request_expected_call(client: Any, expected: str, instruction: str) -> ToolCall:
    messages = [
        {
            "role": "system",
            "content": (
                "This is a native tool-calling smoke test. Call exactly the requested function "
                "with exactly the requested arguments. Do not answer with text or pseudo-JSON."
            ),
        },
        {"role": "user", "content": instruction},
    ]
    list(client.ask_stream("", messages=messages))
    raw_calls = client.get_last_tool_calls()
    if len(raw_calls) != 1:
        raise RuntimeError(f"Expected one {expected} call, received {len(raw_calls)}.")
    call = normalize_tool_call(raw_calls[0], f"smoke_{expected}")
    if call.name != expected:
        raise RuntimeError(f"Expected {expected}, received {call.name}.")
    return call


def run_live_tool_smoke(client: Any) -> list[str]:
    """Exercise model selection and real filesystem tools in an isolated directory."""
    completed: list[str] = []
    with TemporaryDirectory(prefix="citadex-tool-smoke-") as temporary:
        try:
            registry = create_tool_registry(temporary, auto_approve=True)
            stages = (
                (
                    "create_file",
                    (
                        "Call create_file with exactly these JSON arguments: "
                        f'{{"path":"{E2E_PATH}","content":"{E2E_CONTENT}"}}.'
                    ),
                ),
                ("read_file", f"Call read_file with path={E2E_PATH}."),
                ("delete_file", f"Call delete_file with path={E2E_PATH}."),
            )
            for expected, instruction in stages:
                call = _request_expected_call(client, expected, instruction)
                result = registry.execute(call)
                if result.status is not ToolStatus.SUCCESS:
                    message = result.error.message if result.error is not None else "unknown error"
                    raise RuntimeError(f"{expected} failed: {message}")
                if expected == "read_file" and result.content.get("content") != E2E_CONTENT:
                    raise RuntimeError("read_file returned unexpected content.")
                completed.append(expected)
        finally:
            close_project_logger(temporary)
    return completed


__all__ = [
    "E2E_CONTENT",
    "E2E_PATH",
    "SMOKE_PATH",
    "check_native_tool_calling",
    "run_live_tool_smoke",
]
