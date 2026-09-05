from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from quant_research.outcome_evaluator import (
    EpisodeType,
    InMemoryOutcomeRepository,
    OutcomeEvaluationInput,
    aggregate_outcomes,
    evaluate_outcome,
)

CALENDAR = (date(2026, 9, 4), date(2026, 9, 7), date(2026, 9, 8))


def request(episode_type: EpisodeType = EpisodeType.FILLED) -> OutcomeEvaluationInput:
    return OutcomeEvaluationInput(
        decision_id="decision-1",
        proposal_version=1,
        episode_type=episode_type,
        decision_date=date(2026, 9, 4),
        horizon_trading_days=2,
        entry_price=Decimal(10),
        benchmark_entry_price=Decimal(100),
        realized_cost=Decimal("0.01"),
        evidence_ids=("evidence:decision-1",),
    )


def test_outcome_uses_trading_days_and_computes_deterministic_metrics() -> None:
    outcome = evaluate_outcome(
        request(),
        CALENDAR,
        (Decimal(10), Decimal(12), Decimal(11)),
        (Decimal(100), Decimal(101), Decimal(102)),
        datetime(2026, 9, 8, 23, 59, tzinfo=UTC),
    )
    assert outcome.evaluation_available_at.date() == date(2026, 9, 8)
    assert outcome.maximum_favorable_excursion == Decimal("0.2")
    assert outcome.maximum_adverse_excursion == Decimal(0)
    assert outcome.benchmark_excess_return == Decimal("0.08")


def test_outcome_cannot_read_before_window_closes() -> None:
    with pytest.raises(ValueError, match="not closed"):
        evaluate_outcome(
            request(),
            CALENDAR,
            (Decimal(10), Decimal(11), Decimal(12)),
            (Decimal(100), Decimal(101), Decimal(102)),
            datetime(2026, 9, 7, 23, 59, tzinfo=UTC),
        )


def test_repository_is_idempotent_and_corrections_append_versions() -> None:
    repository = InMemoryOutcomeRepository()
    first = evaluate_outcome(
        request(),
        CALENDAR,
        (Decimal(10), Decimal(11), Decimal(12)),
        (Decimal(100), Decimal(101), Decimal(102)),
        datetime(2026, 9, 8, 23, 59, tzinfo=UTC),
    )
    assert repository.save(first).version == 1
    assert repository.save(first).version == 1
    corrected = first.model_copy(update={"content_hash": "f" * 64})
    assert repository.save(corrected).version == 2
    assert len(repository.versions("decision-1", 1)) == 2


def test_episode_types_do_not_mix_return_populations() -> None:
    filled = evaluate_outcome(
        request(EpisodeType.FILLED),
        CALENDAR,
        (Decimal(10), Decimal(11), Decimal(12)),
        (Decimal(100), Decimal(101), Decimal(102)),
        datetime(2026, 9, 8, 23, 59, tzinfo=UTC),
    )
    shadow = evaluate_outcome(
        request(EpisodeType.SHADOW),
        CALENDAR,
        (Decimal(10), Decimal(9), Decimal(8)),
        (Decimal(100), Decimal(101), Decimal(102)),
        datetime(2026, 9, 8, 23, 59, tzinfo=UTC),
    )
    assert aggregate_outcomes((filled, shadow), EpisodeType.FILLED) == (filled,)
    assert aggregate_outcomes((filled, shadow), EpisodeType.SHADOW) == (shadow,)
