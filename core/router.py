"""Deterministic intent routing between chat and agent execution."""

from __future__ import annotations

import re
from enum import Enum


class PromptIntent(str, Enum):
    CHAT = "chat"
    READ_ONLY = "read_only"
    ACTION = "action"


_EXPLANATION_PATTERNS = (
    r"\b(?:how|why|what|explain|tell me|show me how)\b",
    r"\b(?:как|почему|что|объясни|расскажи|покажи как)\b",
)
_ACTION_PATTERNS = (
    r"\b(?:write|create|refactor|fix|edit|implement|generate|add|update|delete|build|run)\b",
    r"\b(?:напиши|создай|исправь|измени|сделай|добавь|удали|поправь|сгенерируй|выполни|запусти)\b",
)
_READ_ONLY_PATTERNS = (
    r"\b(?:check|inspect|review|analy[sz]e|find|search|read|diagnose|test)\b",
    r"\b(?:проверь|посмотри|проанализируй|найди|поищи|прочитай|диагностируй|тестируй)\b",
)
_CODE_CONTEXT = re.compile(
    r"(?:\bcode\b|\bproject\b|\bfile\b|\brepo(?:sitory)?\b|\bкод\w*\b|\bпроект\w*\b|\bфайл\w*\b|[\w.-]+\.[a-z0-9]{1,8})",
    re.IGNORECASE,
)


def detect_intent(prompt: str | None) -> PromptIntent:
    """Classify whether a prompt asks for conversation, inspection, or mutation."""
    text = (prompt or "").strip().casefold()
    if not text:
        return PromptIntent.CHAT
    if any(re.search(pattern, text) for pattern in _EXPLANATION_PATTERNS):
        if re.search(r"\b(?:what|что)\b", text) and _CODE_CONTEXT.search(text):
            return PromptIntent.READ_ONLY
        if not any(re.search(pattern, text) for pattern in _READ_ONLY_PATTERNS):
            return PromptIntent.CHAT
        return PromptIntent.READ_ONLY if _CODE_CONTEXT.search(text) else PromptIntent.CHAT
    if any(re.search(pattern, text) for pattern in _ACTION_PATTERNS):
        return PromptIntent.ACTION
    if any(re.search(pattern, text) for pattern in _READ_ONLY_PATTERNS) and _CODE_CONTEXT.search(text):
        return PromptIntent.READ_ONLY
    return PromptIntent.CHAT


def classify_prompt(prompt: str | None) -> str:
    """Backward-compatible model route: workspace intents use the code model."""
    return "code" if detect_intent(prompt) is not PromptIntent.CHAT else "chat"


def should_use_agent(agent_enabled: bool, prompt: str | None) -> bool:
    return agent_enabled and detect_intent(prompt) is not PromptIntent.CHAT


def is_read_only_intent(prompt: str | None) -> bool:
    return detect_intent(prompt) is PromptIntent.READ_ONLY


__all__ = ["PromptIntent", "classify_prompt", "detect_intent", "is_read_only_intent", "should_use_agent"]
