from datetime import UTC, datetime

import pytest

from src.monitoring import Quote, Watchlist, WatchlistEntry, aggregate_closed_bars


def test_aggregation_is_order_independent_and_only_closed_windows() -> None:
    quotes = [
        Quote(security_id="SSE:1", timestamp="2026-09-04T01:04:00Z", price=11, volume=2, amount=22),
        Quote(security_id="SSE:1", timestamp="2026-09-04T01:01:00Z", price=10, volume=1, amount=10),
        Quote(security_id="SSE:1", timestamp="2026-09-04T01:10:00Z", price=12, volume=1, amount=12),
    ]
    bars = aggregate_closed_bars(quotes, datetime(2026, 9, 4, 1, 10, tzinfo=UTC))
    assert len(bars) == 1
    assert (bars[0].open, bars[0].close, bars[0].high, bars[0].volume) == (10, 11, 11, 3)


def test_watchlist_rejects_more_than_fifty_symbols() -> None:
    watchlist = Watchlist(version="v1", entries=[WatchlistEntry(security_id=f"SSE:{i}", tier="P1") for i in range(51)])
    with pytest.raises(ValueError, match="50"):
        watchlist.validate_capacity()
