# core/provider_manager.py
"""Единый менеджер провайдеров — абстракция над NVIDIA/Gemini/Ollama."""

from __future__ import annotations
import os
from typing import Optional, List
from dotenv import load_dotenv

load_dotenv()


# Список всех доступных моделей по провайдерам
PROVIDER_MODELS = {
    "gemini": [
        "gemini-2.0-flash",       # бесплатно, быстро
        "gemini-2.5-pro",         # бесплатно 25 req/day, умный
        "gemini-1.5-flash",       # старый, стабильный
    ],
    "nvidia": [
        "meta/llama-3.1-8b-instruct",   # быстрый
        "meta/llama-3.3-70b-instruct",  # умный
        "mistralai/mistral-7b-instruct-v0.3",
        "google/gemma-3-27b-it",
    ],
    "ollama": [],  # заполняется динамически при подключении
}


class ProviderManager:
    """Создаёт и хранит текущего LLM-клиента. Поддерживает переключение."""

    def __init__(self, system_prompt: str = "You are a helpful assistant."):
        self.system_prompt = system_prompt
        self._client = None
        self._provider: str = os.getenv("LLM_PROVIDER", "gemini").lower()
        self._model_chat: str = ""
        self._model_code: str = ""

    @property
    def provider(self) -> str:
        return self._provider

    @property
    def current_model(self) -> str:
        return self._model_chat

    def get_client(self):
        """Вернуть текущего клиента (создать если нет)."""
        if self._client is None:
            self._client = self._create_client(self._provider)
        return self._client

    def switch(self, provider: str, model_chat: str, model_code: Optional[str] = None) -> bool:
        """
        Переключить провайдера и модель.
        Возвращает True если успешно, False если ключ не найден.
        """
        provider = provider.lower()
        model_code = model_code or model_chat

        try:
            new_client = self._create_client(provider, model_chat, model_code)
            self._client = new_client
            self._provider = provider
            self._model_chat = model_chat
            self._model_code = model_code
            return True
        except Exception as e:
            print(f"[ProviderManager] switch failed: {e}")
            return False

    def _create_client(self, provider: str, model_chat: str = "", model_code: str = ""):
        if provider == "gemini":
            from core.gemini_client import GeminiClient
            api_key = os.getenv("GEMINI_API_KEY", "")
            if not api_key:
                raise ValueError("GEMINI_API_KEY не задан в .env")
            chat = model_chat or os.getenv("GEMINI_MODEL_CHAT", "gemini-2.0-flash")
            code = model_code or os.getenv("GEMINI_MODEL_CODE", "gemini-2.5-pro")
            return GeminiClient(api_key=api_key, system_prompt=self.system_prompt,
                                model_chat=chat, model_code=code)

        elif provider == "nvidia":
            from core.llm_client import NVIDIAClient
            api_key = os.getenv("NVIDIA_API_KEY", "")
            if not api_key or api_key.startswith("nvapi-xxx"):
                raise ValueError("NVIDIA_API_KEY не задан в .env")
            chat = model_chat or os.getenv("NVIDIA_MODEL_CHAT", "meta/llama-3.1-8b-instruct")
            code = model_code or os.getenv("NVIDIA_MODEL_CODE", "meta/llama-3.3-70b-instruct")
            return NVIDIAClient(api_key, system_prompt=self.system_prompt,
                                model_chat=chat, model_code=code)

        elif provider == "ollama":
            from core.ollama_client import OllamaClient
            chat = model_chat or "llama3.2"
            code = model_code or "codellama"
            return OllamaClient(system_prompt=self.system_prompt,
                                model_chat=chat, model_code=code)

        else:
            raise ValueError(f"Неизвестный провайдер: {provider}")

    def get_available_models(self, provider: str) -> List[str]:
        """Список моделей для выпадающего списка в GUI."""
        if provider == "ollama":
            try:
                from core.ollama_client import OllamaClient
                client = OllamaClient(system_prompt="")
                models = client.list_models()
                return models if models else ["llama3.2", "codellama", "mistral"]
            except Exception:
                return ["llama3.2", "codellama", "mistral"]
        return PROVIDER_MODELS.get(provider, [])

    def reset_history(self):
        if self._client:
            self._client.reset_history()
