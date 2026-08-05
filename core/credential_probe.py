"""Fast provider credential checks that avoid model-catalog discovery."""

from __future__ import annotations

from openai import OpenAI

from core.provider_runtime import fast_probe_timeout

PROBE_CONFIG = {
    "nvidia": "https://integrate.api.nvidia.com/v1",
    "openai": None,
}


def probe_provider_key(provider: str, api_key: str) -> None:
    """Perform one tiny completion with no hidden SDK retries."""
    normalized = provider.casefold()
    if normalized not in PROBE_CONFIG:
        raise ValueError(f"Проверка ключа не поддерживается для {provider}.")
    if not api_key.strip():
        raise ValueError(f"API-ключ {provider.upper()} не настроен.")
    base_url = PROBE_CONFIG[normalized]
    if base_url is None:
        client = OpenAI(api_key=api_key, timeout=fast_probe_timeout(), max_retries=0)
    else:
        client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=fast_probe_timeout(),
            max_retries=0,
        )
    client.models.list()


__all__ = ["PROBE_CONFIG", "probe_provider_key"]
