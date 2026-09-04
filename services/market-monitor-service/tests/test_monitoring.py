from datetime import UTC, datetime

import pytest

from src.monitoring import Quote, Watchlist, WatchlistEntry, aggregate_closed_bars


def test_aggregation_is_order_independent_and_only_closed_windows() -> None:
    quotes = [
        Quote(security_id="SSE:1", timestamp="2026-09-04T01:34:00Z", price=11, volume=2, amount=22),
        Quote(security_id="SSE:1", timestamp="2026-09-04T01:31:00Z", price=10, volume=1, amount=10),
        Quote(security_id="SSE:1", timestamp="2026-09-04T01:40:00Z", price=12, volume=1, amount=12),
    ]
    bars = aggregate_closed_bars(quotes, datetime(2026, 9, 4, 1, 40, tzinfo=UTC))
    assert len(bars) == 1
    assert (bars[0].open, bars[0].close, bars[0].high, bars[0].volume) == (10, 11, 11, 3)


def test_watchlist_rejects_more_than_fifty_symbols() -> None:
    watchlist = Watchlist(version="v1", entries=[WatchlistEntry(security_id=f"SSE:{i}", tier="P1") for i in range(51)])
    with pytest.raises(ValueError, match="50"):
        watchlist.validate_capacity()


def test_lunch_break_is_excluded_and_suspension_is_warn() -> None:
    quotes = [
        Quote(security_id="SSE:1", timestamp="2026-09-04T03:29:00Z", price=10, volume=1, amount=10, trading_status="SUSPENDED"),
        Quote(security_id="SSE:1", timestamp="2026-09-04T03:26:00Z", price=10, volume=0, amount=0),
    ]
    bars = aggregate_closed_bars(quotes, datetime(2026, 9, 4, 6, tzinfo=UTC))
    assert len(bars) == 1
    assert bars[0].quality == "WARN"
    assert bars[0].window_start.hour == 11
