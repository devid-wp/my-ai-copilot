"""Cached native tool-calling compatibility probes for cloud models."""

from __future__ import annotations

from enum import Enum
from hashlib import sha256

from openai import OpenAI

from core.credential_probe import PROBE_CONFIG
from core.provider_runtime import fast_probe_timeout


class ToolCompatibility(str, Enum):
    SUPPORTED = "supported"
    UNRELIABLE = "unreliable"


_cloud_cache: dict[tuple[str, str, bytes], ToolCompatibility] = {}


def probe_cloud_tool_support(provider: str, model: str, api_key: str) -> ToolCompatibility:
    """Request one harmless native call and cache the result by key fingerprint."""
    normalized = provider.casefold()
    if normalized not in PROBE_CONFIG:
        raise ValueError(f"Cloud tool probe is not supported for {provider}.")
    if not api_key.strip():
        raise ValueError(f"API key is not configured for {provider}.")
    cache_key = (normalized, model, sha256(api_key.encode("utf-8")).digest())
    if cache_key in _cloud_cache:
        return _cloud_cache[cache_key]

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
    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "user",
                "content": "Call compatibility_probe with value=ok. Do not answer with text.",
            }
        ],
        tools=[
            {
                "type": "function",
                "function": {
                    "name": "compatibility_probe",
                    "description": "Verify native tool calling support.",
                    "parameters": {
                        "type": "object",
                        "properties": {"value": {"type": "string", "enum": ["ok"]}},
                        "required": ["value"],
                    },
                },
            }
        ],
        tool_choice="auto",
        max_tokens=32,
        temperature=0,
        stream=False,
    )
    message = response.choices[0].message if response.choices else None
    supported = any(
        getattr(getattr(call, "function", None), "name", "") == "compatibility_probe"
        for call in (getattr(message, "tool_calls", None) or [])
    )
    result = ToolCompatibility.SUPPORTED if supported else ToolCompatibility.UNRELIABLE
    _cloud_cache[cache_key] = result
    return result


def clear_cloud_tool_cache() -> None:
    _cloud_cache.clear()


__all__ = [
    "ToolCompatibility",
    "clear_cloud_tool_cache",
    "probe_cloud_tool_support",
]
