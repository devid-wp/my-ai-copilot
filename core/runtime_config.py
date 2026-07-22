"""Small validated runtime settings shared by provider adapters."""

from __future__ import annotations

import os


def response_token_limit() -> int:
    try:
        value = int(os.getenv("CITADEX_MAX_RESPONSE_TOKENS", "2048"))
    except ValueError:
        return 2048
    return min(8192, max(256, value))


def response_temperature() -> float:
    try:
        value = float(os.getenv("CITADEX_TEMPERATURE", "0.2"))
    except ValueError:
        return 0.2
    return min(1.0, max(0.0, value))


__all__ = ["response_temperature", "response_token_limit"]
