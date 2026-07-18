"""NVIDIA NIM client with streaming tool-call support."""

from __future__ import annotations

from collections.abc import Generator
from typing import Any

from openai import OpenAI

from core.functions import FUNCTION_DEFINITIONS
from core.router import classify_prompt

TOOLS = [{"type": "function", "function": definition} for definition in FUNCTION_DEFINITIONS]


class NVIDIAClient:
    def __init__(
        self,
        api_key: str,
        system_prompt: str,
        model_chat: str = "meta/llama-3.1-8b-instruct",
        model_code: str = "meta/llama-3.3-70b-instruct",
        base_url: str = "https://integrate.api.nvidia.com/v1",
    ) -> None:
        if not api_key:
            raise ValueError("NVIDIA_API_KEY is required")
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.system_prompt = system_prompt
        self.model_chat = model_chat
        self.model_code = model_code
        self.history: list[dict[str, Any]] = []
        self._last_tool_calls: list[dict[str, Any]] = []

    def select_model(self, prompt: str) -> str:
        return self.model_code if classify_prompt(prompt) == "code" else self.model_chat

    def ask_stream(
        self,
        prompt: str,
        context: str = "",
        messages: list[dict[str, Any]] | None = None,
    ) -> Generator[str, None, None]:
        external_messages = messages is not None
        if messages is None:
            messages = [{"role": "system", "content": self.system_prompt}, *self.history]
            if prompt:
                messages.append({"role": "user", "content": prompt})

        routing_prompt = prompt
        if not routing_prompt:
            routing_prompt = next(
                (str(m.get("content", "")) for m in reversed(messages) if m.get("role") == "user"),
                "",
            )

        tool_buffers: dict[int, dict[str, Any]] = {}
        content: list[str] = []
        stream = self.client.chat.completions.create(  # type: ignore[call-overload]
            model=self.select_model(routing_prompt),
            messages=self._clean_messages(messages),
            temperature=0.4,
            max_tokens=4096,
            stream=True,
            tools=TOOLS,
            tool_choice="auto",
        )
        for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            for tool_delta in getattr(delta, "tool_calls", None) or []:
                buffer = tool_buffers.setdefault(
                    tool_delta.index,
                    {"id": "", "type": "function", "function": {"name": "", "arguments": ""}},
                )
                if tool_delta.id:
                    buffer["id"] += tool_delta.id
                if tool_delta.function:
                    buffer["function"]["name"] += tool_delta.function.name or ""
                    buffer["function"]["arguments"] += tool_delta.function.arguments or ""
            if delta.content:
                content.append(delta.content)
                yield delta.content

        self._last_tool_calls = list(tool_buffers.values())
        if not external_messages:
            if prompt:
                self.history.append({"role": "user", "content": prompt})
            message: dict[str, Any] = {"role": "assistant", "content": "".join(content)}
            if self._last_tool_calls:
                message["tool_calls"] = self._last_tool_calls
            self.history.append(message)
            self.history = self.history[-20:]

    def ask(self, prompt: str, context: str = "") -> str:
        return "".join(self.ask_stream(prompt, context))

    def get_last_tool_calls(self) -> list[dict[str, Any]]:
        return self._last_tool_calls

    def reset_history(self) -> None:
        self.history.clear()

    @staticmethod
    def _clean_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        clean: list[dict[str, Any]] = []
        for message in messages:
            item = {"role": message.get("role", "user"), "content": message.get("content") or ""}
            if message.get("tool_calls"):
                item["tool_calls"] = message["tool_calls"]
            if message.get("tool_call_id"):
                item["tool_call_id"] = message["tool_call_id"]
            if message.get("name"):
                item["name"] = message["name"]
            clean.append(item)
        return clean
