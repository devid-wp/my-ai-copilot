# core/ollama_client.py
import json
from collections.abc import Generator
from typing import Any

import httpx


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
            # Строим из переданной истории
            ollama_messages = []
            for m in messages:
                role = m.get("role", "user")
                content = m.get("content", "")
                if role == "system":
                    continue  # system передаётся отдельно
                if role == "tool":
                    ollama_messages.append({"role": "user", "content": f"[Tool result]: {content}"})
                elif role == "assistant":
                    ollama_messages.append({"role": "assistant", "content": content})
                else:
                    ollama_messages.append({"role": "user", "content": content})
        else:
            ollama_messages = list(self.history)
            if prompt:
                ollama_messages.append({"role": "user", "content": prompt})

        model_prompt = prompt or (ollama_messages[-1]["content"] if ollama_messages else "")
        selected = self.select_model(model_prompt)

        payload = {
            "model": selected,
            "messages": ollama_messages,
            "system": self.system_prompt,
            "stream": True,
            "options": {"temperature": 0.5, "num_predict": 4096},
        }

        try:
            with httpx.stream(
                "POST",
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=120,
            ) as response:
                for line in response.iter_lines():
                    if not line:
                        continue
                    try:
                        chunk = json.loads(line)
                        token = chunk.get("message", {}).get("content", "")
                        if token:
                            full_response.append(token)
                            yield token
                        if chunk.get("done"):
                            break
                    except json.JSONDecodeError:
                        continue
        except httpx.ConnectError:
            yield "\n[❌ Ollama недоступен. Запустите: ollama serve]"
        except Exception as e:
            yield f"\n[❌ Ошибка Ollama: {e}]"

        if not external_messages:
            if prompt:
                self.history.append({"role": "user", "content": prompt})
            self.history.append({"role": "assistant", "content": "".join(full_response)})
            if len(self.history) > 20:
                self.history = self.history[-20:]

    def get_last_tool_calls(self) -> list:
        return []  # Ollama не поддерживает tool-calling в базовом варианте

    def reset_history(self) -> None:
        self.history.clear()

    def ask(self, prompt: str, context: str = "") -> str:
        return "".join(self.ask_stream(prompt, context))
