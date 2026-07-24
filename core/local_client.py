"""OpenAI-compatible client for the bundled llama.cpp server."""

from __future__ import annotations

import httpx
from openai import OpenAI

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
        super().__init__(
            "local",
            system_prompt,
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
        calls = response.choices[0].message.tool_calls or []
        if any(
            getattr(getattr(call, "function", None), "name", None) == "compatibility_probe"
            for call in calls
        ):
            return ToolCompatibility.SUPPORTED
        return ToolCompatibility.UNRELIABLE


__all__ = ["LocalClient"]
