from datetime import UTC, date, datetime
from decimal import Decimal

from market_data.domain import Exchange, SecurityId
from market_data.pit import (
    CorporateAction,
    DailyBar,
    FinancialFact,
    RawArtifact,
    point_in_time_facts,
    visible_actions,
)
from market_data.quality import QualityStatus, validate_daily_bars


def artifact() -> RawArtifact:
    return RawArtifact(
        source="fixture",
        source_record_id="r1",
        source_version="fixture-1",
        raw_artifact_uri="minio://artifacts/fixtures/r1.json",
        raw_artifact_hash="a" * 64,
        license_ref="test-only",
        source_policy_version="fixture-v1",
        ingested_at=datetime.now(UTC),
    )


def test_pit_hides_future_financial_revision() -> None:
    security_id = SecurityId(exchange=Exchange.SSE, symbol="600000")
    old = FinancialFact(security_id=security_id, fact_type="revenue", period_end=date(2025, 12, 31), value=Decimal(100), announced_at=datetime(2026, 3, 1, tzinfo=UTC), available_at=datetime(2026, 3, 2, tzinfo=UTC), revision=1, artifact=artifact())
    correction = FinancialFact(
        security_id=security_id,
        fact_type="revenue",
        period_end=date(2025, 12, 31),
        value=Decimal(120),
        announced_at=datetime(2026, 4, 1, tzinfo=UTC),
        available_at=datetime(2026, 4, 2, tzinfo=UTC),
        revision=2,
        revision_reason="CORRECTED_DISCLOSURE",
        supersedes_revision=1,
        artifact=artifact(),
    )
    assert point_in_time_facts([old, correction], datetime(2026, 3, 20, tzinfo=UTC))[0].value == Decimal(100)


def test_invalid_or_duplicate_bar_fails_quality() -> None:
    bar = DailyBar(security_id=SecurityId(exchange=Exchange.SSE, symbol="600000"), trading_day=date(2026, 8, 28), open=Decimal(10), high=Decimal(9), low=Decimal(8), close=Decimal(10), volume=Decimal(1), amount=Decimal(10), available_at=datetime(2026, 8, 28, 7, tzinfo=UTC), artifact=artifact())
    assert validate_daily_bars([bar, bar]).status is QualityStatus.FAIL


def test_corporate_action_is_not_visible_before_available_at() -> None:
    action = CorporateAction(security_id=SecurityId(exchange=Exchange.SSE, symbol="600000"), action_type="DIVIDEND", ex_date=date(2026, 6, 20), available_at=datetime(2026, 6, 19, 8, tzinfo=UTC), adjustment_factor=Decimal("0.98"), artifact=artifact())
    assert visible_actions([action], datetime(2026, 6, 18, tzinfo=UTC)) == []
