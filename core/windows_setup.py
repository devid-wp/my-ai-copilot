"""One-click Windows bootstrap for Citadex and its local Ollama model."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from pathlib import Path

from core.preferences import UserPreferences, save_preferences

DEFAULT_LOCAL_MODEL = "qwen2.5-coder:1.5b"
OLLAMA_API = "http://127.0.0.1:11434"


def find_ollama() -> str | None:
    installed = shutil.which("ollama")
    if installed:
        return installed
    local_app_data = os.getenv("LOCALAPPDATA")
    if local_app_data:
        candidate = Path(local_app_data) / "Programs" / "Ollama" / "ollama.exe"
        if candidate.is_file():
            return str(candidate)
    return None


def ollama_models(base_url: str = OLLAMA_API) -> set[str]:
    try:
        with urllib.request.urlopen(f"{base_url}/api/tags", timeout=3) as response:
            payload = json.load(response)
    except (OSError, ValueError, urllib.error.URLError):
        return set()
    return {str(model.get("name", "")) for model in payload.get("models", [])}


def install_ollama() -> str:
    winget = shutil.which("winget")
    if not winget:
        raise RuntimeError(
            "Не найден winget. Установите Ollama с https://ollama.com/download/windows и повторите запуск."
        )
    result = subprocess.run(
        [
            winget,
            "install",
            "--id",
            "Ollama.Ollama",
            "-e",
            "--accept-package-agreements",
            "--accept-source-agreements",
        ],
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Ollama не установлена (код {result.returncode}).")
    executable = find_ollama()
    if not executable:
        raise RuntimeError("Ollama установлена, но ollama.exe не найден. Перезапустите Citadex.")
    return executable


def start_ollama(executable: str, timeout: float = 20) -> None:
    if ollama_models() or _ollama_online():
        return
    flags = 0
    if os.name == "nt":
        flags = subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS
    subprocess.Popen(
        [executable, "serve"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=flags,
    )
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if _ollama_online():
            return
        time.sleep(0.5)
    raise RuntimeError("Ollama не запустилась за 20 секунд.")


def _ollama_online(base_url: str = OLLAMA_API) -> bool:
    try:
        with urllib.request.urlopen(f"{base_url}/api/version", timeout=2) as response:
            return response.status == 200
    except (OSError, urllib.error.URLError):
        return False


def pull_model(executable: str, model: str = DEFAULT_LOCAL_MODEL) -> None:
    if model in ollama_models():
        return
    result = subprocess.run([executable, "pull", model], check=False)
    if result.returncode != 0:
        raise RuntimeError(f"Не удалось скачать модель {model} (код {result.returncode}).")


def configure_local_defaults(model: str = DEFAULT_LOCAL_MODEL) -> None:
    save_preferences(
        UserPreferences(
            provider="ollama",
            mode="agent",
            permissions="ask",
            models={"ollama": model},
            project_root=str(Path.cwd().resolve()),
            recent_projects=[str(Path.cwd().resolve())],
        )
    )


def bootstrap_local_model(
    confirm: Callable[[str], bool],
    model: str = DEFAULT_LOCAL_MODEL,
) -> str:
    executable = find_ollama()
    if executable is None:
        if not confirm("Ollama не найдена. Установить её через winget?"):
            raise RuntimeError("Установка Ollama отменена пользователем.")
        executable = install_ollama()
    start_ollama(executable)
    if model not in ollama_models():
        if not confirm(f"Скачать локальную модель {model} (около 1 ГБ)?"):
            raise RuntimeError("Загрузка модели отменена пользователем.")
        pull_model(executable, model)
    configure_local_defaults(model)
    return model


__all__ = [
    "DEFAULT_LOCAL_MODEL",
    "bootstrap_local_model",
    "configure_local_defaults",
    "find_ollama",
    "install_ollama",
    "ollama_models",
    "pull_model",
    "start_ollama",
]
