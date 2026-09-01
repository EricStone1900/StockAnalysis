from datetime import UTC, date, datetime
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
from quant_research.evaluation import (
    EvaluationWindow,
    FactorEvaluationError,
    FactorReturnObservation,
    FactorValueObservation,
    QuantileEvaluationConfig,
    TemporalSplitDefinition,
    WalkForwardConfig,
    build_walk_forward_plan,
    evaluate_factor_correlation,
    evaluate_factor_stability,
    evaluate_information_coefficients,
    evaluate_quantile_performance,
    split_factor_observations,
    split_walk_forward_observations,
)
from quant_research.factors import (
    CandidateFactorEvidence,
    CandidateFactorRecord,
    FactorCategory,
    FactorDefinition,
    FactorVersion,
    admit_price_factor_candidate,
)


def _ref(uri: str, character: str) -> ArtifactRef:
    return ArtifactRef(uri=uri, sha256=character * 64)


def candidate() -> CandidateFactorRecord:
    version = MarketDataVersionRef(
        version_id="cn-a-fixture-v1",
        artifact=_ref("minio://artifacts/qlib", "a"),
        close_gap_index=_ref("minio://artifacts/gaps", "b"),
        quality_status=DataQualityStatus.WARN,
        source_release_tag="fixture",
        source_policy_version="v1",
    )
    policy = CloseGapHandlingPolicy(
        policy_version="v1",
        artifact=_ref("minio://artifacts/policy", "c"),
        applicable_universe_version="cn-a-main-board-v1",
        approval_reference="ADR-003-04",
        acknowledged_by="tester",
        approved_at=datetime(2026, 1, 3, tzinfo=UTC),
    )
    manifest = build_run_manifest("evaluation-fixture", resolve_close_gaps(version, policy, (), datetime(2026, 1, 3, tzinfo=UTC))).model_copy(
        update={
            "factor_matrix_artifact": _ref("minio://artifacts/factor", "d"),
            "factor_matrix_canonical_content_hash": "e" * 64,
            "factor_transform_version": "raw-price-v1",
        }
    )
    return admit_price_factor_candidate(
        FactorDefinition(
            factor_id="price.momentum.2d",
            category=FactorCategory.PRICE_MOMENTUM,
            required_fields=("close",),
            lookback_trading_days=2,
        ),
        FactorVersion(
            factor_id="price.momentum.2d",
            version="v1",
            expression_hash="a" * 64,
            data_version_id="cn-a-fixture-v1",
            transform_version="raw-price-v1",
        ),
        CandidateFactorEvidence(
            run_manifest=manifest,
            run_manifest_artifact=_ref("minio://artifacts/run", "f"),
            matrix_factor_ids=("price.momentum.2d",),
        ),
        approval_reference="ADR-003-09",
    )


def window(*, end_date: date = date(2026, 1, 2)) -> EvaluationWindow:
    return EvaluationWindow(
        start_date=date(2026, 1, 2),
        end_date=end_date,
        cutoff_at=datetime.combine(end_date, datetime.max.time(), tzinfo=UTC),
    )


def observation(security_id: str, factor: str, realized_return: str) -> FactorReturnObservation:
    return FactorReturnObservation(
        security_id=security_id,
        as_of_date=date(2026, 1, 2),
        feature_available_at=datetime(2026, 1, 2, 16, tzinfo=UTC),
        forward_return_start=date(2026, 1, 5),
        forward_return_end=date(2026, 1, 5),
        factor_value=Decimal(factor),
        realized_return=Decimal(realized_return),
    )


def test_information_coefficients_are_stable_and_use_only_forward_returns() -> None:
    report = evaluate_information_coefficients(
        candidate(),
        window(),
        (
            observation("sz000001", "1", "0.01"),
            observation("sh600000", "2", "0.02"),
            observation("sz000002", "3", "0.03"),
        ),
    )

    result = report.daily_information_coefficients[0]
    assert result.information_coefficient == Decimal("1.00000000")
    assert result.rank_information_coefficient == Decimal("1.00000000")
    assert report.eligibility == "RESEARCH_ONLY"


def test_evaluation_rejects_current_day_return_label() -> None:
    with pytest.raises(ValueError, match="start after"):
        FactorReturnObservation(
            security_id="sh600000",
            as_of_date=date(2026, 1, 2),
            feature_available_at=datetime(2026, 1, 2, 16, tzinfo=UTC),
            forward_return_start=date(2026, 1, 2),
            forward_return_end=date(2026, 1, 2),
            factor_value=Decimal(1),
            realized_return=Decimal("0.01"),
        )
    with pytest.raises(FactorEvaluationError, match="constant"):
        evaluate_information_coefficients(
            candidate(),
            window(),
            (observation("sh600000", "1", "0.01"), observation("sz000001", "1", "0.02")),
        )


def test_quantile_returns_and_turnover_are_deterministic() -> None:
    next_day = date(2026, 1, 5)
    second_cross_section = tuple(
        observation(security_id, factor, realized_return).model_copy(
            update={
                "as_of_date": next_day,
                "feature_available_at": datetime(2026, 1, 5, 16, tzinfo=UTC),
                "forward_return_start": date(2026, 1, 6),
                "forward_return_end": date(2026, 1, 6),
            }
        )
        for security_id, factor, realized_return in (
            ("sh600000", "4", "0.04"),
            ("sz000001", "1", "0.01"),
            ("sz000002", "2", "0.02"),
            ("sz000003", "3", "0.03"),
        )
    )
    report = evaluate_quantile_performance(
        candidate(),
        window(end_date=next_day),
        QuantileEvaluationConfig(quantile_count=2),
        (
            observation("sh600000", "1", "0.01"),
            observation("sz000001", "2", "0.02"),
            observation("sz000002", "3", "0.03"),
            observation("sz000003", "4", "0.04"),
            *second_cross_section,
        ),
    )

    first, second = report.daily_performance
    assert first.long_short_return == Decimal("0.02000000")
    assert first.top_quantile_replacement_rate is None
    assert second.top_quantile_replacement_rate == Decimal("0.66666667")


def test_factor_correlation_uses_only_paired_rows_and_stability_is_reproducible() -> None:
    report = evaluate_information_coefficients(
        candidate(),
        EvaluationWindow(
            start_date=date(2026, 1, 2),
            end_date=date(2026, 1, 5),
            cutoff_at=datetime(2026, 1, 5, 23, tzinfo=UTC),
        ),
        (
            observation("sh600000", "1", "0.01"),
            observation("sz000001", "2", "0.02"),
            observation("sh600000", "1", "0.02").model_copy(
                update={
                    "as_of_date": date(2026, 1, 5),
                    "feature_available_at": datetime(2026, 1, 5, 16, tzinfo=UTC),
                    "forward_return_start": date(2026, 1, 6),
                    "forward_return_end": date(2026, 1, 6),
                }
            ),
            observation("sz000001", "2", "0.01").model_copy(
                update={
                    "as_of_date": date(2026, 1, 5),
                    "feature_available_at": datetime(2026, 1, 5, 16, tzinfo=UTC),
                    "forward_return_start": date(2026, 1, 6),
                    "forward_return_end": date(2026, 1, 6),
                }
            ),
        ),
    )
    stability = evaluate_factor_stability(report)
    assert stability.observation_day_count == 2
    assert stability.positive_information_coefficient_rate == Decimal("0.50000000")

    corr = evaluate_factor_correlation(
        window(end_date=date(2026, 1, 5)),
        tuple(
            FactorValueObservation(
                security_id=security_id,
                as_of_date=date(2026, 1, 2),
                feature_available_at=datetime(2026, 1, 2, 16, tzinfo=UTC),
                factor_id=factor_id,
                factor_value=Decimal(value),
            )
            for security_id, factor_id, value in (
                ("sh600000", "price.momentum.2d", "1"),
                ("sh600000", "price.volatility.2d", "2"),
                ("sz000001", "price.momentum.2d", "2"),
                ("sz000001", "price.volatility.2d", "1"),
            )
        ),
    )
    assert corr.correlations[0].correlation == Decimal("-1.00000000")


def test_temporal_split_is_ordered_and_rejects_cross_boundary_labels() -> None:
    split = TemporalSplitDefinition(
        train_start=date(2026, 1, 2), train_end=date(2026, 1, 5),
        validation_start=date(2026, 1, 6), validation_end=date(2026, 1, 9),
        test_start=date(2026, 1, 12), test_end=date(2026, 1, 15),
    )
    train = observation("sh600000", "1", "0.01")
    validation = observation("sh600000", "2", "0.02").model_copy(
        update={
            "as_of_date": date(2026, 1, 6),
            "feature_available_at": datetime(2026, 1, 6, 16, tzinfo=UTC),
            "forward_return_start": date(2026, 1, 7),
            "forward_return_end": date(2026, 1, 7),
        }
    )
    test = observation("sh600000", "3", "0.03").model_copy(
        update={
            "as_of_date": date(2026, 1, 12),
            "feature_available_at": datetime(2026, 1, 12, 16, tzinfo=UTC),
            "forward_return_start": date(2026, 1, 13),
            "forward_return_end": date(2026, 1, 13),
        }
    )
    dataset = split_factor_observations(candidate(), split, (train, validation, test))
    reordered = split_factor_observations(candidate(), split, (test, train, validation))
    assert len(dataset.train) == len(dataset.validation) == len(dataset.test) == 1
    assert dataset.canonical_content_hash == reordered.canonical_content_hash

    crossing = train.model_copy(update={"forward_return_end": date(2026, 1, 6)})
    with pytest.raises(FactorEvaluationError, match="crosses"):
        split_factor_observations(candidate(), split, (crossing, validation, test))

    with pytest.raises(ValueError, match="ordered"):
        TemporalSplitDefinition(
            train_start=date(2026, 1, 2), train_end=date(2026, 1, 9),
            validation_start=date(2026, 1, 6), validation_end=date(2026, 1, 9),
            test_start=date(2026, 1, 12), test_end=date(2026, 1, 15),
        )


def test_walk_forward_plan_rolls_over_trading_days_without_randomization() -> None:
    trading_days = tuple(date(2026, 1, day) for day in range(2, 12))
    config = WalkForwardConfig(train_size=3, validation_size=2, test_size=2, step_size=2)
    plan = build_walk_forward_plan(trading_days, config)
    assert len(plan.splits) == 2
    assert plan.splits[0].train_start == date(2026, 1, 2)
    assert plan.splits[1].train_start == date(2026, 1, 4)
    assert plan.splits[0].test_end < plan.splits[1].test_end

    observations = tuple(
        observation("sh600000", str(index), "0.01").model_copy(
            update={
                "as_of_date": trading_day,
                "feature_available_at": datetime.combine(trading_day, datetime.min.time(), tzinfo=UTC),
                "forward_return_start": trading_days[min(index + 1, len(trading_days) - 1)],
                "forward_return_end": trading_days[min(index + 1, len(trading_days) - 1)],
            }
        )
        for index, trading_day in enumerate(trading_days[:-1])
    )
    with pytest.raises(FactorEvaluationError, match="crosses"):
        split_walk_forward_observations(candidate(), plan, observations)

    with pytest.raises(FactorEvaluationError, match="sorted"):
        build_walk_forward_plan(tuple(reversed(trading_days)), config)
