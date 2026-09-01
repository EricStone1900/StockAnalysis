from datetime import UTC, date, datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from quant_research.domain import (
    ArtifactRef,
    CloseGap,
    CloseGapHandlingPolicy,
    DataQualityStatus,
    MarketDataVersionRef,
    resolve_close_gaps,
)


def artifact(suffix: str) -> ArtifactRef:
    digest_prefix = {"archive": "a", "close-gap-index": "c", "policy": "d"}[suffix]
    return ArtifactRef(uri=f"minio://artifacts/{suffix}", sha256=digest_prefix * 64)


def data_version() -> MarketDataVersionRef:
    return MarketDataVersionRef(
        version_id="cn-a-investment-data-2026-08-29-aeecdc530b93",
        artifact=artifact("archive"),
        close_gap_index=artifact("close-gap-index"),
        quality_status=DataQualityStatus.WARN,
        source_release_tag="2026-08-29",
        source_policy_version="v1-close-gap-fast",
    )


def policy() -> CloseGapHandlingPolicy:
    return CloseGapHandlingPolicy(
        policy_version="v1-assume-suspension-on-read",
        artifact=artifact("policy"),
        applicable_universe_version="cn-a-main-board-v1",
        approval_reference="ADR-003-01",
        acknowledged_by="research-operator",
        approved_at=datetime(2026, 8, 30, tzinfo=UTC),
    )


def test_close_gap_resolution_is_sorted_and_deterministic() -> None:
    gaps = (
        CloseGap(security_id="sz000001", trading_day=date(2020, 1, 3)),
        CloseGap(security_id="sh600000", trading_day=date(2020, 1, 2)),
    )
    first = resolve_close_gaps(data_version(), policy(), gaps, datetime(2026, 8, 30, tzinfo=UTC))
    second = resolve_close_gaps(data_version(), policy(), tuple(reversed(gaps)), datetime(2026, 8, 31, tzinfo=UTC))

    assert [entry.security_id for entry in first.entries] == ["sh600000", "sz000001"]
    assert all(entry.status == "SUSPENSION_ASSUMED" for entry in first.entries)
    assert first.canonical_content_hash == second.canonical_content_hash
    assert first.quality_status is DataQualityStatus.WARN


def test_policy_requires_approval_and_utc_timestamp() -> None:
    values = policy().model_dump()
    values["approval_reference"] = ""
    with pytest.raises(ValidationError):
        CloseGapHandlingPolicy.model_validate(values)

    values = policy().model_dump()
    values["approved_at"] = datetime(2026, 8, 30, tzinfo=timezone(timedelta(hours=8)))
    with pytest.raises(ValidationError):
        CloseGapHandlingPolicy.model_validate(values)


def test_resolution_rejects_non_utc_generation_time() -> None:
    with pytest.raises(ValueError, match="generated_at must use UTC"):
        resolve_close_gaps(
            data_version(),
            policy(),
            (),
            datetime(2026, 8, 30, tzinfo=timezone(timedelta(hours=8))),
        )


def test_failed_data_version_is_rejected() -> None:
    values = data_version().model_dump()
    values["quality_status"] = DataQualityStatus.FAIL
    with pytest.raises(ValidationError, match="FAIL DataVersion"):
        MarketDataVersionRef.model_validate(values)
