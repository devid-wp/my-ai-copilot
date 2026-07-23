"""Provider-backed model discovery with a short in-process cache."""

from __future__ import annotations

import os
from hashlib import sha256
from time import monotonic

from openai import OpenAI

NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"
NVIDIA_MODEL_FALLBACKS = (
    "meta/llama-3.1-8b-instruct",
    "meta/llama-3.3-70b-instruct",
)
NVIDIA_MENU_LIMIT = 12
RECOMMENDED_MODEL_PATTERNS = (
    "meta/llama-3.1-8b-instruct",
    "meta/llama-3.3-70b-instruct",
    "step-3.5-flash",
    "deepseek-v4-flash",
    "nemotron-mini-4b",
    "nvidia-nemotron-nano-9b",
    "mistral-nemo-12b",
    "qwen3-next",
    "gpt-oss-20b",
    "gemma-3-12b",
    "codestral-22b",
    "glm-5.2",
)
NON_CHAT_MARKERS = (
    "embed",
    "rerank",
    "retriever",
    "vision",
    "-vl",
    "clip",
    "detector",
    "safety",
    "guard",
    "reward",
    "translate",
    "deplot",
    "fuyu",
    "parse",
    "calibration",
    "cosmos",
    "kosmos",
    "neva",
    "vila",
)
CHAT_MARKERS = (
    "instruct",
    "chat",
    "coder",
    "reasoning",
    "reason",
    "flash",
    "pro",
    "gpt-oss",
    "glm",
    "jamba",
    "kimi",
    "laguna",
    "mistral",
    "mixtral",
    "qwen",
    "gemma",
    "llama",
    "nemotron",
    "minimax",
    "inkling",
)
MODEL_CACHE_SECONDS = 300
_nvidia_cache: tuple[float, bytes, tuple[str, ...]] | None = None


def is_nvidia_chat_model(model: str) -> bool:
    """Conservatively keep models intended for text generation."""
    lowered = model.casefold()
    return not any(marker in lowered for marker in NON_CHAT_MARKERS) and any(
        marker in lowered for marker in CHAT_MARKERS
    )


def _model_rank(model: str) -> tuple[int, int, str]:
    """Prefer fast instruct/tool candidates while keeping stable alphabetical order."""
    lowered = model.casefold()
    preferred = next(
        (index for index, candidate in enumerate(NVIDIA_MODEL_FALLBACKS) if model == candidate),
        len(NVIDIA_MODEL_FALLBACKS),
    )
    slow_markers = ("reason", "pro", "120b", "253b", "340b", "550b", "675b")
    slow_penalty = 1 if any(marker in lowered for marker in slow_markers) else 0
    return preferred, slow_penalty, lowered


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
    discovered = {str(item.id) for item in response.data if getattr(item, "id", None)}
    models = tuple(sorted((model for model in discovered if is_nvidia_chat_model(model)), key=_model_rank))
    if not models:
        raise RuntimeError("NVIDIA API returned no compatible text chat models for this key.")
    _nvidia_cache = (now, fingerprint, models)
    return list(models)


def recommended_nvidia_models(api_key: str, limit: int = NVIDIA_MENU_LIMIT) -> list[str]:
    """Return a compact menu; exact model IDs remain usable through `/model ID`."""
    models = nvidia_models(api_key)
    selected: list[str] = []
    for pattern in RECOMMENDED_MODEL_PATTERNS:
        match = next(
            (
                model
                for model in models
                if model not in selected and pattern in model.casefold()
            ),
            None,
        )
        if match is not None:
            selected.append(match)
        if len(selected) >= limit:
            return selected
    selected.extend(model for model in models if model not in selected)
    return selected[:limit]


def select_nvidia_model(api_key: str, preferred: str | None = None) -> str:
    models = nvidia_models(api_key)
    configured = preferred or os.getenv("NVIDIA_MODEL") or os.getenv("NVIDIA_MODEL_CODE")
    if configured and configured in models:
        return configured
    for candidate in NVIDIA_MODEL_FALLBACKS:
        if candidate in models:
            return candidate
    return models[0]


def clear_model_cache() -> None:
    global _nvidia_cache
    _nvidia_cache = None


__all__ = [
    "clear_model_cache",
    "is_nvidia_chat_model",
    "nvidia_models",
    "recommended_nvidia_models",
    "select_nvidia_model",
]
