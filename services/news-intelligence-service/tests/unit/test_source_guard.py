from datetime import UTC, datetime, timedelta

import pytest

from src.source_guard import SourceGuard, SourcePolicy


def test_guard_enforces_license_and_rate_limit() -> None:
    guard = SourceGuard()
    policy = SourcePolicy("official", archive_allowed=True, requests_per_minute=2)
    now = datetime(2026, 9, 4, 1, tzinfo=UTC)
    guard.check(policy, now)
    guard.check(policy, now + timedelta(seconds=1))
    with pytest.raises(TimeoutError, match="rate limit"):
        guard.check(policy, now + timedelta(seconds=2))
    with pytest.raises(PermissionError, match="forbids"):
        guard.check(SourcePolicy("blocked", archive_allowed=False), now)


def test_failed_source_fails_closed_until_recovery() -> None:
    guard = SourceGuard()
    policy = SourcePolicy("vendor", archive_allowed=True)
    now = datetime(2026, 9, 4, 1, tzinfo=UTC)
    guard.mark_failed(policy.source_id)
    assert guard.status(policy.source_id) == "STALE"
    with pytest.raises(ConnectionError, match="unavailable"):
        guard.check(policy, now)
    guard.mark_recovered(policy.source_id)
    assert guard.status(policy.source_id) == "AVAILABLE"
    guard.check(policy, now)
