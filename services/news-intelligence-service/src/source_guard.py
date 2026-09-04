"""新闻来源的许可、限流和故障保护。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta


@dataclass(frozen=True)
class SourcePolicy:
    source_id: str
    archive_allowed: bool
    requests_per_minute: int = 60


class SourceGuard:
    def __init__(self) -> None:
        self._windows: dict[str, list[datetime]] = {}
        self._failed: set[str] = set()

    def check(self, policy: SourcePolicy, now: datetime) -> None:
        if now.tzinfo is None:
            raise ValueError("source guard timestamp must include timezone")
        if not policy.archive_allowed:
            raise PermissionError("source license policy forbids archival")
        if policy.requests_per_minute < 1:
            raise ValueError("requests_per_minute must be positive")
        if policy.source_id in self._failed:
            raise ConnectionError("source is unavailable")
        current = now.astimezone(UTC)
        window = [stamp for stamp in self._windows.get(policy.source_id, []) if current - stamp < timedelta(minutes=1)]
        if len(window) >= policy.requests_per_minute:
            raise TimeoutError("source rate limit exceeded")
        window.append(current)
        self._windows[policy.source_id] = window

    def mark_failed(self, source_id: str) -> None:
        self._failed.add(source_id)

    def mark_recovered(self, source_id: str) -> None:
        self._failed.discard(source_id)

    def status(self, source_id: str) -> str:
        return "STALE" if source_id in self._failed else "AVAILABLE"
