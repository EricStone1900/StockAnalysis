from datetime import date

import pytest

from market_data.domain import Exchange, SecurityId
from market_data.status_batches import StatusBatchState, plan_status_batches
from market_data.status_enrichment import CloseGap


def test_status_batches_are_deterministic_and_ordered() -> None:
    gaps = (
        CloseGap(security_id=SecurityId(exchange=Exchange.SSE, symbol="600001"), trading_day=date(2025, 1, 2)),
        CloseGap(security_id=SecurityId(exchange=Exchange.SSE, symbol="600000"), trading_day=date(2025, 1, 3)),
        CloseGap(security_id=SecurityId(exchange=Exchange.SSE, symbol="600000"), trading_day=date(2025, 1, 2)),
    )
    first = plan_status_batches(gaps, 2)
    second = plan_status_batches(reversed(gaps), 2)

    assert first == second
    assert [batch.gap_count for batch in first] == [2, 1]
    assert first[0].first_key == "SSE:600000:2025-01-02"
    assert first[0].state is StatusBatchState.PENDING


def test_status_batches_reject_non_positive_size() -> None:
    with pytest.raises(ValueError, match="positive"):
        plan_status_batches((), 0)


def test_status_batch_namespace_prevents_cross_policy_identity_collisions() -> None:
    gaps = (CloseGap(security_id=SecurityId(exchange=Exchange.SSE, symbol="600000"), trading_day=date(2025, 1, 2)),)

    exact = plan_status_batches(gaps, 1)
    fast = plan_status_batches(gaps, 1, identity_namespace="parent-v1:v1-close-gap-fast")

    assert exact[0].batch_id != fast[0].batch_id
