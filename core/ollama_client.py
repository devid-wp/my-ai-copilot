# core/ollama_client.py
import json
from collections.abc import Generator
from enum import Enum
from functools import lru_cache
from typing import Any

import httpx

from core.router import classify_prompt
from core.runtime_config import response_temperature, response_token_limit
from core.tool_protocol import provider_tool_schemas

TOOLS = provider_tool_schemas()


class ToolCompatibility(str, Enum):
    SUPPORTED = "supported"
    UNRELIABLE = "unreliable"


class OllamaClient:
    """Клиент для локального Ollama — такой же интерфейс как NVIDIAClient."""

    def __init__(
        self,
        system_prompt: str,
        model_chat: str = "llama3.2",
        model_code: str = "codellama",
        base_url: str = "http://localhost:11434",
    ):
        self.system_prompt = system_prompt
        self.model_chat = model_chat
        self.model_code = model_code
        self.base_url = base_url
        self.history: list[dict[str, Any]] = []
        self._last_tool_calls: list[dict[str, Any]] = []

    def is_available(self) -> bool:
        """Проверить что Ollama запущен."""
        try:
            r = httpx.get(f"{self.base_url}/api/tags", timeout=2)
            return r.status_code == 200
        except Exception:
            return False

    def list_models(self) -> list[str]:
        """Список установленных моделей."""
        try:
            r = httpx.get(f"{self.base_url}/api/tags", timeout=5)
            data = r.json()
            return [m["name"] for m in data.get("models", [])]
        except Exception:
            return []

    def check_tool_support(self, model: str) -> ToolCompatibility:
        return probe_tool_support(self.base_url, model)

    def select_model(self, prompt: str) -> str:
        return self.model_code if classify_prompt(prompt) == "code" else self.model_chat

    def ask_stream(
        self,
        prompt: str,
        context: str = "",
        messages: list[dict[str, Any]] | None = None,
    ) -> Generator[str, None, None]:
        self._last_tool_calls = []
        external_messages = messages is not None
        full_response: list[str] = []

        if messages is not None:
            ollama_messages = self._clean_messages(messages)
        else:
            ollama_messages = [
                {"role": "system", "content": self.system_prompt},
                *self.history,
            ]
            if prompt:
                ollama_messages.append({"role": "user", "content": prompt})

        model_prompt = prompt or (ollama_messages[-1]["content"] if ollama_messages else "")
        selected = self.select_model(model_prompt)

        payload = {
            "model": selected,
            "messages": ollama_messages,
            "stream": True,
            "options": {
                "temperature": response_temperature(),
                "num_predict": response_token_limit(),
            },
        }
        if external_messages:
            payload["tools"] = TOOLS

        try:
            with httpx.stream(
                "POST",
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=120,
            ) as response:
                try:
                    response.raise_for_status()
                except httpx.HTTPStatusError:
                    # Streaming responses do not preload their body. Read it
                    # before building the user-facing error below.
                    response.read()
                    raise
                for line in response.iter_lines():
                    if not line:
                        continue
                    try:
                        chunk = json.loads(line)
                        message = chunk.get("message", {})
                        token = message.get("content", "")
                        if token:
                            full_response.append(token)
                            yield token
                        for raw_call in message.get("tool_calls") or []:
                            function = raw_call.get("function") or {}
                            arguments = function.get("arguments") or {}
                            if isinstance(arguments, str):
                                try:
                                    arguments = json.loads(arguments)
                                except json.JSONDecodeError:
                                    arguments = {}
                            self._last_tool_calls.append(
                                {
                                    "id": raw_call.get("id")
                                    or f"ollama_call_{len(self._last_tool_calls) + 1}",
                                    "type": "function",
                                    "function": {
                                        "name": str(function.get("name") or ""),
                                        "arguments": json.dumps(arguments, ensure_ascii=False),
                                    },
                                }
                            )
                        if chunk.get("done"):
                            break
                    except (AttributeError, json.JSONDecodeError):
                        continue
        except httpx.ConnectError:
            raise RuntimeError("Ollama недоступен. Запустите локальный сервер Ollama.") from None
        except httpx.HTTPStatusError as exc:
            try:
                detail = exc.response.json().get("error", exc.response.text)
            except (AttributeError, json.JSONDecodeError):
                detail = exc.response.text
            raise RuntimeError(f"Ollama HTTP {exc.response.status_code}: {detail}") from exc

        if not external_messages:
            if prompt:
                self.history.append({"role": "user", "content": prompt})
            self.history.append({"role": "assistant", "content": "".join(full_response)})
            if len(self.history) > 20:
                self.history = self.history[-20:]

    def get_last_tool_calls(self) -> list[dict[str, Any]]:
        return self._last_tool_calls

    def reset_history(self) -> None:
        self.history.clear()

    def ask(self, prompt: str, context: str = "") -> str:
        return "".join(self.ask_stream(prompt, context))

    @staticmethod
    def _clean_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        clean: list[dict[str, Any]] = []
        for message in messages:
            role = str(message.get("role", "user"))
            item: dict[str, Any] = {
                "role": role,
                "content": str(message.get("content") or ""),
            }
            if role == "assistant" and message.get("tool_calls"):
                calls: list[dict[str, Any]] = []
                for raw_call in message["tool_calls"]:
                    function = raw_call.get("function") or {}
                    arguments = function.get("arguments") or {}
                    if isinstance(arguments, str):
                        try:
                            arguments = json.loads(arguments)
                        except json.JSONDecodeError:
                            arguments = {}
                    calls.append(
                        {
                            "function": {
                                "name": str(function.get("name") or ""),
                                "arguments": arguments,
                            }
                        }
                    )
                item["tool_calls"] = calls
            if role == "tool" and message.get("name"):
                item["tool_name"] = str(message["name"])
            clean.append(item)
        return clean


@lru_cache(maxsize=64)
def probe_tool_support(base_url: str, model: str) -> ToolCompatibility:
    """Ask a model for one harmless native call without executing the tool."""
    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": ("Call compatibility_probe now with value set to ok. Do not answer with text."),
            }
        ],
        "stream": False,
        "options": {"temperature": 0, "num_predict": 64},
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "compatibility_probe",
                    "description": "Verify native tool calling support.",
                    "parameters": {
                        "type": "object",
                        "properties": {"value": {"type": "string", "enum": ["ok"]}},
                        "required": ["value"],
                    },
                },
            }
        ],
    }
    try:
        response = httpx.post(f"{base_url}/api/chat", json=payload, timeout=120)
        response.raise_for_status()
        message = response.json().get("message") or {}
    except (httpx.HTTPError, ValueError) as exc:
        raise RuntimeError(f"Не удалось проверить tools модели {model}: {exc}") from exc

    for tool_call in message.get("tool_calls") or []:
        function = tool_call.get("function") or {}
        if function.get("name") == "compatibility_probe":
            return ToolCompatibility.SUPPORTED
    return ToolCompatibility.UNRELIABLE


__all__ = ["OllamaClient", "ToolCompatibility", "probe_tool_support"]
