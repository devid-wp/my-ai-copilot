# core/ollama_client.py
import json
from collections.abc import Generator
from typing import Any

import httpx

from core.functions import FUNCTION_DEFINITIONS

TOOLS = [{"type": "function", "function": definition} for definition in FUNCTION_DEFINITIONS]


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

    def select_model(self, prompt: str) -> str:
        from core.router import classify_prompt

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
            "options": {"temperature": 0.5, "num_predict": 4096},
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
                response.raise_for_status()
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
