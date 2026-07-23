"""Fast provider credential checks that avoid model-catalog discovery."""

from __future__ import annotations

from openai import OpenAI

from core.provider_catalog import NVIDIA_BASE_URL
from core.provider_runtime import fast_probe_timeout

PROBE_CONFIG = {
    "nvidia": (
        NVIDIA_BASE_URL,
        "meta/llama-3.1-8b-instruct",
    ),
    "gemini": (
        "https://generativelanguage.googleapis.com/v1beta/openai/",
        "gemini-2.0-flash",
    ),
}


def probe_provider_key(provider: str, api_key: str) -> None:
    """Perform one tiny completion with no hidden SDK retries."""
    normalized = provider.casefold()
    if normalized not in PROBE_CONFIG:
        raise ValueError(f"Проверка ключа не поддерживается для {provider}.")
    if not api_key.strip():
        raise ValueError(f"API-ключ {provider.upper()} не настроен.")
    base_url, model = PROBE_CONFIG[normalized]
    client = OpenAI(
        api_key=api_key,
        base_url=base_url,
        timeout=fast_probe_timeout(),
        max_retries=0,
    )
    client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": "Reply only with OK."}],
        max_tokens=2,
        temperature=0,
        stream=False,
    )


__all__ = ["PROBE_CONFIG", "probe_provider_key"]
