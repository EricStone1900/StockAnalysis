from datetime import UTC, datetime, timedelta
from hashlib import sha256

from market_data.operations import (
    DAILY_BAR_SLO,
    ProviderPolicy,
    SourceSelector,
    is_stale,
    verify_artifact,
)


def test_artifact_hash_mismatch_is_rejected() -> None:
    assert verify_artifact(b"artifact", sha256(b"artifact").hexdigest())
    assert not verify_artifact(b"artifact", "0" * 64)


def test_primary_failure_switches_source() -> None:
    primary = ProviderPolicy("primary", "licensed", 10, 1.0, 3)
    fallback = ProviderPolicy("fallback", "licensed", 5, 2.0, 2)
    assert SourceSelector(primary, fallback).select(False) == (fallback, True)


def test_daily_data_freshness_threshold() -> None:
    now = datetime(2026, 8, 29, tzinfo=UTC)
    assert is_stale(now - timedelta(hours=19), now, DAILY_BAR_SLO)
