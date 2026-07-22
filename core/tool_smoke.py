"""Live provider smoke test for native tool calling."""

from __future__ import annotations

from typing import Any

from core.tool_protocol import normalize_tool_call

SMOKE_PATH = "pyproject.toml"


def test_native_tool_calling(client: Any) -> str:
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


__all__ = ["SMOKE_PATH", "test_native_tool_calling"]
