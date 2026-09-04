from datetime import UTC, datetime

import pytest

from src.monitoring import MonitorPolicy, Watchlist, WatchlistEntry, due_tiers


def test_tier_schedule_reuses_one_batch_snapshot() -> None:
    policy = MonitorPolicy(version="policy-v1")
    last = datetime(2026, 9, 4, 1, tzinfo=UTC)
    assert due_tiers(policy, last, datetime(2026, 9, 4, 1, 10, tzinfo=UTC)) == ("P0",)
    assert due_tiers(policy, last, datetime(2026, 9, 4, 1, 20, tzinfo=UTC)) == ("P0", "P1")
    assert due_tiers(policy, last, datetime(2026, 9, 4, 1, 30, tzinfo=UTC)) == ("P0", "P1", "P2")


def test_policy_rejects_custom_intervals_or_large_watchlist() -> None:
    watchlist = Watchlist(version="v1", entries=[WatchlistEntry(security_id=f"SSE:{i}", tier="P1") for i in range(51)])
    with pytest.raises(ValueError, match="50"):
        MonitorPolicy(version="v1").validate_for_watchlist(watchlist)
    with pytest.raises(ValueError, match="fixed"):
        MonitorPolicy(version="v1", intervals_minutes={"P0": 1, "P1": 2, "P2": 3}).validate_for_watchlist(
            Watchlist(version="v1", entries=[])
        )
