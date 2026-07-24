"""OpenAI-compatible client for the bundled llama.cpp server."""

from __future__ import annotations

import json
from collections.abc import Generator
from typing import Any

import httpx
from openai import OpenAI

from core.agent_loop import parse_pseudo_tool_call
from core.llm_client import NVIDIAClient
from core.local_runtime import LOCAL_BASE_URL, LOCAL_MODEL_ID
from core.tool_compatibility import ToolCompatibility


class LocalClient(NVIDIAClient):
    def __init__(
        self,
        system_prompt: str,
        model: str = LOCAL_MODEL_ID,
        base_url: str = f"{LOCAL_BASE_URL}/v1",
    ) -> None:
        self.system_prompt_suffix = (
            "\n\nLOCAL TOOL FORMAT: When a tool is needed, output exactly one JSON object "
            'with keys "name" and "arguments". Do not use Markdown fences, explanations, '
            "or multiple calls in one response. After receiving a tool result, either make "
            "exactly one next call or answer normally if the task is complete."
        )
        super().__init__(
            "local",
            system_prompt + self.system_prompt_suffix,
            model_chat=model,
            model_code=model,
            base_url=base_url,
        )
        self.provider_name = "LOCAL QWEN"
        self.client = OpenAI(
            api_key="local",
            base_url=base_url,
            timeout=httpx.Timeout(180, connect=10),
            max_retries=0,
        )

    def ask_stream(
        self,
        prompt: str,
        context: str = "",
        messages: list[dict[str, Any]] | None = None,
    ) -> Generator[str, None, None]:
        chunks: list[str] = []
        for chunk in super().ask_stream(prompt, context, messages):
            chunks.append(chunk)
            yield chunk
        if messages is None or self._last_tool_calls:
            return
        fallback = parse_pseudo_tool_call("".join(chunks))
        if fallback is not None:
            self._last_tool_calls = [
                {
                    "id": "local_json_call_0",
                    "type": "function",
                    "function": {
                        "name": fallback["name"],
                        "arguments": json.dumps(
                            fallback["arguments"],
                            ensure_ascii=False,
                        ),
                    },
                }
            ]

    def check_tool_support(self, model: str = LOCAL_MODEL_ID) -> ToolCompatibility:
        response = self.client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": "Call compatibility_probe with value ok. Do not answer with text.",
                }
            ],
            tools=[
                {
                    "type": "function",
                    "function": {
                        "name": "compatibility_probe",
                        "description": "Verify native tool calling.",
                        "parameters": {
                            "type": "object",
                            "properties": {"value": {"type": "string", "enum": ["ok"]}},
                            "required": ["value"],
                        },
                    },
                }
            ],
            tool_choice="auto",
            temperature=0,
            max_tokens=64,
        )
        message = response.choices[0].message
        calls = message.tool_calls or []
        if any(
            getattr(getattr(call, "function", None), "name", None) == "compatibility_probe"
            for call in calls
        ):
            return ToolCompatibility.SUPPORTED
        fallback = parse_pseudo_tool_call(message.content or "")
        if fallback is not None and fallback["name"] == "compatibility_probe":
            return ToolCompatibility.SUPPORTED
        return ToolCompatibility.UNRELIABLE


__all__ = ["LocalClient"]
