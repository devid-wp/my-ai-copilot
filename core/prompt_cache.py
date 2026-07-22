"""Lazy invalidation cache for expensive agent system prompts."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass


@dataclass(slots=True)
class PromptCache:
    builder: Callable[[], str]
    _value: str | None = None

    def get(self) -> str:
        if self._value is None:
            self._value = self.builder()
        return self._value

    def invalidate(self) -> None:
        self._value = None


__all__ = ["PromptCache"]
