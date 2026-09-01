from datetime import UTC, date, datetime, timedelta, timezone
from decimal import Decimal

import pytest

from quant_research.domain import (
    ArtifactRef,
    CloseGapHandlingPolicy,
    DataQualityStatus,
    MarketDataVersionRef,
    build_run_manifest,
    resolve_close_gaps,
)
from quant_research.factors import (
    CandidateFactorEvidence,
    FactorCategory,
    FactorDefinition,
    FactorPromotionError,
    FactorStatus,
    FactorVersion,
    admit_price_factor_candidate,
    build_active_factor_set,
    promote_to_candidate,
)
from quant_research.universe import (
    HistoricalUniverseDefinition,
    UniverseEligibilityInput,
    build_historical_universe,
)


def definition() -> HistoricalUniverseDefinition:
    return HistoricalUniverseDefinition(
        universe_id="cn-a-main-board",
        version="v1",
        as_of_date=date(2020, 1, 31),
        cutoff_at=datetime(2020, 1, 31, 8, tzinfo=UTC),
        min_listed_days=30,
        min_average_daily_turnover=Decimal(1000000),
    )


def input_for(security_id: str, **changes: object) -> UniverseEligibilityInput:
    values: dict[str, object] = {
        "security_id": security_id,
        "listed_on": date(2019, 1, 1),
        "delisted_on": None,
        "status_available_at": datetime(2020, 1, 30, tzinfo=UTC),
        "is_st": False,
        "is_suspended": False,
        "average_daily_turnover": Decimal(2000000),
    }
    values.update(changes)
    return UniverseEligibilityInput.model_validate(values)


def test_historical_universe_excludes_unavailable_or_ineligible_members() -> None:
    future_status = datetime(2020, 1, 31, 9, tzinfo=UTC)
    snapshot = build_historical_universe(
        definition(),
        (
            input_for("sz000001"),
            input_for("sh600000", is_st=True),
            input_for("bj430047"),
            input_for("sz000002", is_suspended=True),
            input_for("sz000003", status_available_at=future_status),
            input_for("sz000004", listed_on=date(2020, 1, 15)),
            input_for("sz000005", delisted_on=date(2020, 1, 31)),
            input_for("sz000006", average_daily_turnover=Decimal(999999)),
        ),
    )

    assert snapshot.members == ("sz000001",)
    assert snapshot.canonical_content_hash == build_historical_universe(
        definition(), (input_for("sz000001"),)
    ).canonical_content_hash


def test_universe_rejects_non_utc_cutoff() -> None:
    values = definition().model_dump()
    values["cutoff_at"] = datetime(2020, 1, 31, tzinfo=timezone(timedelta(hours=8)))
    with pytest.raises(ValueError, match="UTC"):
        HistoricalUniverseDefinition.model_validate(values)


def factor_version() -> FactorVersion:
    return FactorVersion(
        factor_id="value.pe",
        version="v1",
        expression_hash="a" * 64,
        data_version_id="cn-a-fixture-v1",
        transform_version="winsorize-v1",
    )


def test_valuation_factor_cannot_be_candidate_without_pit_data() -> None:
    factor = FactorDefinition(
        factor_id="value.pe",
        category=FactorCategory.VALUE,
        required_fields=("pe",),
        lookback_trading_days=1,
        requires_valuation_pit=True,
    )
    with pytest.raises(FactorPromotionError, match="valuation PIT"):
        promote_to_candidate(
            factor,
            factor_version(),
            price_data_ready=True,
            valuation_pit_ready=False,
            financial_revision_pit_ready=False,
            approval_reference="ADR-003-02",
        )


def test_candidate_cannot_enter_active_factor_set() -> None:
    candidate = factor_version().model_copy(update={"status": FactorStatus.CANDIDATE})
    with pytest.raises(FactorPromotionError, match="only ACTIVE"):
        build_active_factor_set("core", "v1", (candidate,))


def _ref(uri: str, character: str) -> ArtifactRef:
    return ArtifactRef(uri=uri, sha256=character * 64)


def _price_candidate_evidence(
    *, factor_ids: tuple[str, ...] = ("price.momentum.2d",)
) -> CandidateFactorEvidence:
    data_version = MarketDataVersionRef(
        version_id="cn-a-fixture-v1",
        artifact=_ref("minio://artifacts/qlib", "a"),
        close_gap_index=_ref("minio://artifacts/gaps", "b"),
        quality_status=DataQualityStatus.WARN,
        source_release_tag="fixture",
        source_policy_version="v1",
    )
    policy = CloseGapHandlingPolicy(
        policy_version="v1-assume-suspension-on-read",
        artifact=_ref("minio://artifacts/policy", "c"),
        applicable_universe_version="cn-a-main-board-v1",
        approval_reference="ADR-003-04",
        acknowledged_by="tester",
        approved_at=datetime(2026, 8, 30, tzinfo=UTC),
    )
    manifest = build_run_manifest(
        "candidate-fixture-001",
        resolve_close_gaps(data_version, policy, (), datetime(2026, 8, 30, tzinfo=UTC)),
    ).model_copy(
        update={
            "factor_matrix_artifact": _ref("minio://artifacts/factors", "d"),
            "factor_matrix_canonical_content_hash": "e" * 64,
            "factor_transform_version": "raw-price-v1",
        }
    )
    return CandidateFactorEvidence(
        run_manifest=manifest,
        run_manifest_artifact=_ref("minio://artifacts/runs", "f"),
        matrix_factor_ids=factor_ids,
    )


def test_price_factor_candidate_requires_published_warn_evidence_and_is_research_only() -> None:
    definition = FactorDefinition(
        factor_id="price.momentum.2d",
        category=FactorCategory.PRICE_MOMENTUM,
        required_fields=("close",),
        lookback_trading_days=2,
    )
    version = FactorVersion(
        factor_id="price.momentum.2d",
        version="v1",
        expression_hash="a" * 64,
        data_version_id="cn-a-fixture-v1",
        transform_version="raw-price-v1",
    )

    record = admit_price_factor_candidate(
        definition,
        version,
        _price_candidate_evidence(),
        approval_reference="ADR-003-08",
    )

    assert record.factor.status is FactorStatus.CANDIDATE
    assert record.input_quality_status is DataQualityStatus.WARN
    assert record.eligibility == "RESEARCH_ONLY"
    with pytest.raises(FactorPromotionError, match="published factor matrix does not contain"):
        admit_price_factor_candidate(
            definition,
            version,
            _price_candidate_evidence(factor_ids=("price.volatility.2d",)),
            approval_reference="ADR-003-08",
        )
    with pytest.raises(FactorPromotionError, match="non-smoke approval"):
        admit_price_factor_candidate(
            definition,
            version,
            _price_candidate_evidence(),
            approval_reference="stage03-local-smoke",
        )
