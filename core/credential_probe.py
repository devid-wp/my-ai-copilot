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


def validate_provider_model_access(provider: str, model: str, api_key: str) -> None:
    """Reject a manually entered cloud model that is absent from the provider catalog."""
    normalized = provider.casefold()
    if normalized not in PROBE_CONFIG:
        raise ValueError(f"Проверка модели не поддерживается для {provider}.")
    if not model.strip():
        raise ValueError("Имя модели не может быть пустым.")
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
    available = {str(item.id) for item in client.models.list().data if getattr(item, "id", None)}
    if model not in available:
        raise ValueError(
            f"Модель '{model}' недоступна для {provider.upper()} или была удалена. "
            "Проверьте точное имя модели и введите его снова."
        )


__all__ = ["PROBE_CONFIG", "probe_provider_key", "validate_provider_model_access"]
