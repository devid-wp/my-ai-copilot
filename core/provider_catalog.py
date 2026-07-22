"""Provider-backed model discovery with a short in-process cache."""

from __future__ import annotations

import os
from hashlib import sha256
from time import monotonic

from openai import OpenAI

NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"
NVIDIA_MODEL_FALLBACKS = (
    "meta/llama-3.3-70b-instruct",
    "meta/llama-3.1-8b-instruct",
)
MODEL_CACHE_SECONDS = 300
_nvidia_cache: tuple[float, bytes, tuple[str, ...]] | None = None


def nvidia_models(api_key: str, *, refresh: bool = False) -> list[str]:
    """Return models exposed to the current NVIDIA API credential."""
    global _nvidia_cache
    now = monotonic()
    if not api_key.strip():
        raise RuntimeError("NVIDIA API key is required to discover available models.")
    fingerprint = sha256(api_key.encode("utf-8")).digest()
    if (
        not refresh
        and _nvidia_cache is not None
        and _nvidia_cache[1] == fingerprint
        and now - _nvidia_cache[0] < MODEL_CACHE_SECONDS
    ):
        return list(_nvidia_cache[2])
    response = OpenAI(api_key=api_key, base_url=NVIDIA_BASE_URL).models.list()
    models = tuple(sorted({str(item.id) for item in response.data if getattr(item, "id", None)}))
    if not models:
        raise RuntimeError("NVIDIA API returned no available models for this key.")
    _nvidia_cache = (now, fingerprint, models)
    return list(models)


def select_nvidia_model(api_key: str, preferred: str | None = None) -> str:
    models = nvidia_models(api_key)
    configured = preferred or os.getenv("NVIDIA_MODEL") or os.getenv("NVIDIA_MODEL_CODE")
    if configured and configured in models:
        return configured
    for candidate in NVIDIA_MODEL_FALLBACKS:
        if candidate in models:
            return candidate
    likely_chat = [
        model
        for model in models
        if any(marker in model.casefold() for marker in ("instruct", "chat"))
        and not any(marker in model.casefold() for marker in ("embed", "rerank", "vision"))
    ]
    return likely_chat[0] if likely_chat else models[0]


def clear_model_cache() -> None:
    global _nvidia_cache
    _nvidia_cache = None


__all__ = ["clear_model_cache", "nvidia_models", "select_nvidia_model"]
