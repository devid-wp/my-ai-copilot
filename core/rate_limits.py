"""Minute-based provider check cooldowns that avoid exhausting API quotas."""

from __future__ import annotations

from dataclasses import dataclass
from time import monotonic

LIMIT_REFRESH_SECONDS = 60


@dataclass(frozen=True, slots=True)
class LimitSnapshot:
    checked_at: float
    next_check_at: float
    limited: bool
    message: str


class RateLimitMonitor:
    def __init__(self, refresh_seconds: int = LIMIT_REFRESH_SECONDS) -> None:
        self.refresh_seconds = refresh_seconds
        self._snapshots: dict[str, LimitSnapshot] = {}

    def seconds_until_refresh(self, provider: str, now: float | None = None) -> int:
        snapshot = self._snapshots.get(provider)
        if snapshot is None:
            return 0
        current = monotonic() if now is None else now
        return max(0, int(snapshot.next_check_at - current + 0.999))

    def can_check(self, provider: str, now: float | None = None) -> bool:
        return self.seconds_until_refresh(provider, now) == 0

    def record_success(self, provider: str, now: float | None = None) -> LimitSnapshot:
        return self._record(provider, False, "API available", now)

    def record_error(self, provider: str, error: Exception, now: float | None = None) -> LimitSnapshot:
        text = str(error)
        lowered = text.casefold()
        limited = any(
            marker in lowered
            for marker in ("resourceexhausted", "rate limit", "request limit", "too many requests", "429")
        )
        message = "Request limit reached" if limited else text
        return self._record(provider, limited, message, now)

    def describe(self, provider: str, now: float | None = None) -> str:
        snapshot = self._snapshots.get(provider)
        if snapshot is None:
            return "not checked"
        remaining = self.seconds_until_refresh(provider, now)
        state = "limit reached" if snapshot.limited else "available"
        return f"{state}; refresh in {remaining}s" if remaining else f"{state}; ready to refresh"

    def _record(
        self,
        provider: str,
        limited: bool,
        message: str,
        now: float | None,
    ) -> LimitSnapshot:
        current = monotonic() if now is None else now
        snapshot = LimitSnapshot(
            checked_at=current,
            next_check_at=current + self.refresh_seconds,
            limited=limited,
            message=message,
        )
        self._snapshots[provider] = snapshot
        return snapshot


rate_limit_monitor = RateLimitMonitor()

__all__ = [
    "LIMIT_REFRESH_SECONDS",
    "LimitSnapshot",
    "RateLimitMonitor",
    "rate_limit_monitor",
]
