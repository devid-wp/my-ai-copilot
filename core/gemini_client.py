# core/gemini_client.py
from __future__ import annotations
import json
from typing import Any, Dict, Generator, List, Optional
from openai import OpenAI
from core.functions import FUNCTION_DEFINITIONS
from core.router import classify_prompt

TOOLS = [{"type": "function", "function": fn} for fn in FUNCTION_DEFINITIONS]

class GeminiClient:
    def __init__(self, api_key: str, system_prompt: str,
                 model_chat: str = "gemini-2.0-flash",
                 model_code: str = "gemini-2.5-pro") -> None:
        self._client = OpenAI(
            api_key=api_key,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
        )
        self.system_prompt = system_prompt
        self.model_chat = model_chat
        self.model_code = model_code
        self.history: List[Dict[str, Any]] = []
        self._last_tool_calls: List[Dict[str, Any]] = []

    def select_model(self, prompt: str) -> str:
        return self.model_code if classify_prompt(prompt) == "code" else self.model_chat

    def ask_stream(self, prompt: str, context: str = "",
                   messages: Optional[List[Dict[str, Any]]] = None) -> Generator[str, None, None]:
        self._last_tool_calls = []
        _tc_buffer: dict = {}

        if messages is None:
            messages = [{"role": "system", "content": self.system_prompt}]
            messages.extend(self.history)
            if prompt:
                messages.append({"role": "user", "content": prompt})

        model_prompt = prompt
        if not model_prompt and messages:
            for msg in reversed(messages):
                if msg.get("role") == "user":
                    model_prompt = msg.get("content", "")
                    break

        # Clean messages for OpenAI‑compatible endpoint
        clean_messages = []
        for m in messages:
            role = m.get("role", "user")
            if role == "tool":
                clean_messages.append({
                    "role": "tool",
                    "content": m.get("content", ""),
                    "tool_call_id": m.get("tool_call_id", "call_0"),
                })
            else:
                clean_messages.append({
                    "role": role,
                    "content": m.get("content", "") or "",
                })

        selected = self.select_model(model_prompt)
        full_response = []

        stream = self._client.chat.completions.create(
            model=selected,
            messages=clean_messages,
            temperature=0.5,
            max_tokens=4096,
            stream=True,
            tools=TOOLS,
            tool_choice="auto",
        )

        for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta

            if hasattr(delta, "tool_calls") and delta.tool_calls:
                for tc_delta in delta.tool_calls:
                    idx = tc_delta.index
                    if idx not in _tc_buffer:
                        _tc_buffer[idx] = {"id": "", "type": "function",
                                           "function": {"name": "", "arguments": ""}}
                    buf = _tc_buffer[idx]
                    if tc_delta.id:
                        buf["id"] += tc_delta.id
                    if tc_delta.function:
                        if tc_delta.function.name:
                            buf["function"]["name"] += tc_delta.function.name
                        if tc_delta.function.arguments:
                            buf["function"]["arguments"] += tc_delta.function.arguments

            if delta.content:
                full_response.append(delta.content)
                yield delta.content

        self._last_tool_calls = list(_tc_buffer.values())

        if messages is None:
            if prompt:
                self.history.append({"role": "user", "content": prompt})
            msg: dict = {"role": "assistant", "content": "".join(full_response)}
            if self._last_tool_calls:
                msg["tool_calls"] = self._last_tool_calls
            self.history.append(msg)
            if len(self.history) > 20:
                self.history = self.history[-20:]

    def get_last_tool_calls(self) -> List[Dict[str, Any]]:
        return self._last_tool_calls

    def reset_history(self) -> None:
        self.history.clear()

    def ask(self, prompt: str, context: str = "") -> str:
        return "".join(self.ask_stream(prompt, context))
