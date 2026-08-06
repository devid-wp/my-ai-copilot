"""Shared provider request limits and user-facing error diagnostics."""

from __future__ import annotations

import os
from typing import Any

import httpx

DEFAULT_CONNECT_TIMEOUT_SECONDS = 10.0
DEFAULT_FIRST_TOKEN_TIMEOUT_SECONDS = 45.0
DEFAULT_MAX_RETRIES = 1
FAST_PROBE_TIMEOUT_SECONDS = 15.0


def _positive_float(name: str, default: float) -> float:
    try:
        value = float(os.getenv(name, str(default)))
    except ValueError:
        return default
    return value if value > 0 else default


def provider_timeout() -> httpx.Timeout:
    """Bound connection and time-to-first-token waits for streaming APIs."""
    connect = _positive_float("CITADEX_CONNECT_TIMEOUT", DEFAULT_CONNECT_TIMEOUT_SECONDS)
    first_token = _positive_float(
        "CITADEX_FIRST_TOKEN_TIMEOUT", DEFAULT_FIRST_TOKEN_TIMEOUT_SECONDS
    )
    return httpx.Timeout(first_token, connect=connect)


def fast_probe_timeout() -> httpx.Timeout:
    """Short fail-fast timeout for credential checks and model discovery."""
    connect = min(
        _positive_float("CITADEX_CONNECT_TIMEOUT", DEFAULT_CONNECT_TIMEOUT_SECONDS),
        5.0,
    )
    total = _positive_float("CITADEX_PROBE_TIMEOUT", FAST_PROBE_TIMEOUT_SECONDS)
    return httpx.Timeout(total, connect=connect)


def provider_max_retries() -> int:
    try:
        value = int(os.getenv("CITADEX_PROVIDER_RETRIES", str(DEFAULT_MAX_RETRIES)))
    except ValueError:
        return DEFAULT_MAX_RETRIES
    return max(0, min(value, 2))


def provider_name(client: Any) -> str:
    return str(getattr(client, "provider_name", type(client).__name__)).upper()


def explain_provider_error(exc: Exception, provider: str) -> str:
    """Translate SDK/network failures without exposing credentials."""
    text = str(exc)
    lowered = f"{type(exc).__name__} {text}".casefold()
    if any(marker in lowered for marker in ("timeout", "timed out")):
        return (
            f"{provider} не начала отвечать за отведённое время. "
            "Попробуйте ещё раз или выберите более быструю модель."
        )
    if any(marker in lowered for marker in ("429", "rate limit", "resourceexhausted")):
        return f"{provider}: исчерпан лимит запросов. Подождите и повторите позже."
    if any(marker in lowered for marker in ("401", "403", "invalid api key", "authentication")):
        return f"{provider}: API-ключ недействителен или не имеет доступа. Проверьте профиль через /config."
    if any(marker in lowered for marker in ("410", "gone")):
        return (
            f"{provider}: выбранная модель удалена или больше недоступна. "
            "Укажите актуальное имя в профиле через /config."
        )
    if any(
        marker in lowered
        for marker in ("connection", "connecterror", "network", "dns", "name resolution")
    ):
        return f"{provider}: не удалось подключиться к API. Проверьте интернет и доступность сервиса."
    return f"{provider}: запрос завершился ошибкой: {text}"


__all__ = [
    "explain_provider_error",
    "fast_probe_timeout",
    "provider_max_retries",
    "provider_name",
    "provider_timeout",
]
