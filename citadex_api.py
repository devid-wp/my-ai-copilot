"""Beginner-friendly API setup and Citadex launcher."""

from __future__ import annotations

import os
import sys
from getpass import getpass
from pathlib import Path
from typing import Any

from core.credentials import PROVIDER_API_KEYS, save_api_key, validate_api_key
from core.preferences import UserPreferences, save_preferences
from core.tool_smoke import check_native_tool_calling
from main import main as citadex_main


def choose_provider() -> str:
    print("Выберите API-провайдера:\n  1. NVIDIA\n  2. OpenAI")
    while True:
        answer = input("\nНомер [1]: ").strip().casefold()
        if answer in {"", "1", "nvidia"}:
            return "nvidia"
        if answer in {"2", "openai"}:
            return "openai"
        print("Введите 1 или 2.")


def create_api_client(provider: str, api_key: str, model: str) -> Any:
    if provider == "nvidia":
        from core.llm_client import NVIDIAClient

        return NVIDIAClient(api_key, "Citadex tool-calling test", model_chat=model, model_code=model)
    from core.llm_client import OpenAIClient

    return OpenAIClient(api_key, "Citadex tool-calling test", model_chat=model, model_code=model)


def configure_api(provider: str, api_key: str, model: str) -> str:
    key = validate_api_key(provider, api_key)
    model = model.strip()
    if not model:
        raise ValueError("Имя модели не может быть пустым.")
    client = create_api_client(provider, key, model)
    check_native_tool_calling(client)
    save_api_key(provider, key)
    project = str(Path.cwd().resolve())
    save_preferences(
        UserPreferences(
            provider=provider,
            mode="agent",
            permissions="ask",
            models={provider: model},
            project_root=project,
            recent_projects=[project],
        )
    )
    return model


def run() -> int:
    print("\nCITADEX · простая настройка API\n")
    provider = choose_provider()
    environment_name = PROVIDER_API_KEYS[provider]
    existing = os.getenv(environment_name, "").strip()
    label = f"Вставьте {provider.upper()} API-ключ (он будет скрыт)"
    if existing:
        label += " или нажмите Enter, чтобы проверить сохранённый"
    entered = getpass(f"{label}: ").strip()
    api_key = entered or existing
    if not api_key:
        print("\nОшибка: API-ключ не введён.", file=sys.stderr)
        return 2
    model = input("Введите точное имя модели: ").strip()
    if not model:
        print("\nОшибка: имя модели не введено.", file=sys.stderr)
        return 2
    print("\nПроверяю API-ключ и native tool calling...")
    try:
        model = configure_api(provider, api_key, model)
    except Exception as exc:
        print(f"\nПроверка не пройдена: {exc}", file=sys.stderr)
        return 2
    print("✓ API работает\n✓ Native tool calling работает\n✓ Ключ безопасно сохранён\n")
    return citadex_main(
        [
            "--project",
            str(Path.cwd()),
            "--provider",
            provider,
            "--model",
            model,
            "--agent",
            "--skip-setup",
        ]
    )


if __name__ == "__main__":
    raise SystemExit(run())
