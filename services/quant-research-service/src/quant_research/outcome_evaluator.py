"""确定性交易结果评估；只处理已关闭的交易日窗口。"""

from __future__ import annotations

import json
from datetime import UTC, date, datetime
from decimal import Decimal
from enum import StrEnum
from hashlib import sha256
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field, model_validator


class EpisodeType(StrEnum):
    FILLED = "FILLED"
    REJECTED = "REJECTED"
    HOLD = "HOLD"
    EXPIRED = "EXPIRED"
    SHADOW = "SHADOW"


class OutcomeEvaluationInput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    decision_id: str = Field(min_length=1)
    proposal_version: int = Field(ge=1)
    episode_type: EpisodeType
    decision_date: date
    horizon_trading_days: int = Field(ge=1)
    entry_price: Decimal = Field(gt=0)
    benchmark_entry_price: Decimal = Field(gt=0)
    realized_cost: Decimal | None = Field(default=None, ge=0)
    evidence_ids: tuple[str, ...] = ()


class DecisionOutcome(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    outcome_id: str
    version: int = Field(ge=1)
    decision_id: str
    proposal_version: int = Field(ge=1)
    episode_type: EpisodeType
    horizon_trading_days: int = Field(ge=1)
    evaluation_available_at: datetime
    benchmark_excess_return: Decimal
    maximum_favorable_excursion: Decimal
    maximum_adverse_excursion: Decimal
    realized_cost: Decimal | None = None
    evidence_ids: tuple[str, ...] = ()
    content_hash: str = Field(min_length=64, max_length=64)

    @model_validator(mode="after")
    def validate_available_at(self) -> DecisionOutcome:
        if self.evaluation_available_at.tzinfo is None or self.evaluation_available_at.utcoffset() != UTC.utcoffset(self.evaluation_available_at):
            raise ValueError("evaluation_available_at must use UTC")
        return self


class OutcomeRepository(Protocol):
    def save(self, outcome: DecisionOutcome) -> DecisionOutcome: ...
    def versions(self, decision_id: str, proposal_version: int) -> tuple[DecisionOutcome, ...]: ...


class InMemoryOutcomeRepository:
    """更正追加新版本，绝不覆盖历史 Outcome。"""

    def __init__(self) -> None:
        self._outcomes: dict[tuple[str, int], list[DecisionOutcome]] = {}

    def save(self, outcome: DecisionOutcome) -> DecisionOutcome:
        key = (outcome.decision_id, outcome.proposal_version)
        versions = self._outcomes.setdefault(key, [])
        if versions and versions[-1].content_hash == outcome.content_hash:
            return versions[-1]
        saved = outcome.model_copy(update={"version": len(versions) + 1})
        versions.append(saved)
        return saved

    def versions(self, decision_id: str, proposal_version: int) -> tuple[DecisionOutcome, ...]:
        return tuple(self._outcomes.get((decision_id, proposal_version), []))


def evaluate_outcome(
    request: OutcomeEvaluationInput,
    trading_calendar: tuple[date, ...],
    prices: tuple[Decimal, ...],
    benchmark_prices: tuple[Decimal, ...],
    observed_at: datetime,
) -> DecisionOutcome:
    """在窗口关闭后计算收益、MFE 与 MAE；调用方必须提供交易日而非自然日。"""
    if observed_at.tzinfo is None or observed_at.utcoffset() != UTC.utcoffset(observed_at):
        raise ValueError("observed_at must use UTC")
    if tuple(sorted(set(trading_calendar))) != trading_calendar:
        raise ValueError("trading_calendar must be sorted and unique")
    try:
        decision_index = trading_calendar.index(request.decision_date)
    except ValueError as error:
        raise ValueError("decision_date must be a trading day") from error
    end_index = decision_index + request.horizon_trading_days
    if end_index >= len(trading_calendar):
        raise ValueError("trading calendar does not close the evaluation window")
    evaluation_date = trading_calendar[end_index]
    evaluation_available_at = datetime(evaluation_date.year, evaluation_date.month, evaluation_date.day, 23, 59, tzinfo=UTC)
    if observed_at < evaluation_available_at:
        raise ValueError("outcome window is not closed at observed_at")
    if len(prices) != request.horizon_trading_days + 1 or len(benchmark_prices) != len(prices):
        raise ValueError("prices must include the entry and every evaluation trading day")
    if any(price <= 0 for price in (*prices, *benchmark_prices)):
        raise ValueError("prices must be positive")
    asset_returns = tuple((price / request.entry_price) - Decimal(1) for price in prices)
    benchmark_return = (benchmark_prices[-1] / request.benchmark_entry_price) - Decimal(1)
    benchmark_excess_return = asset_returns[-1] - benchmark_return
    maximum_favorable_excursion = max(asset_returns)
    maximum_adverse_excursion = min(asset_returns)
    payload = {
        "decision_id": request.decision_id,
        "proposal_version": request.proposal_version,
        "episode_type": request.episode_type.value,
        "horizon_trading_days": request.horizon_trading_days,
        "evaluation_available_at": evaluation_available_at.isoformat(),
        "benchmark_excess_return": str(benchmark_excess_return),
        "maximum_favorable_excursion": str(maximum_favorable_excursion),
        "maximum_adverse_excursion": str(maximum_adverse_excursion),
        "realized_cost": None if request.realized_cost is None else str(request.realized_cost),
        "evidence_ids": request.evidence_ids,
    }
    content_hash = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return DecisionOutcome(
        outcome_id=f"outcome:{request.decision_id}:{request.proposal_version}", version=1,
        decision_id=request.decision_id, proposal_version=request.proposal_version, episode_type=request.episode_type,
        horizon_trading_days=request.horizon_trading_days, evaluation_available_at=evaluation_available_at,
        benchmark_excess_return=benchmark_excess_return,
        maximum_favorable_excursion=maximum_favorable_excursion,
        maximum_adverse_excursion=maximum_adverse_excursion,
        realized_cost=request.realized_cost, evidence_ids=request.evidence_ids, content_hash=content_hash,
    )


def aggregate_outcomes(outcomes: tuple[DecisionOutcome, ...], episode_type: EpisodeType) -> tuple[DecisionOutcome, ...]:
    """不同 EpisodeType 不共享收益口径，调用方必须显式选择类别。"""
    return tuple(outcome for outcome in outcomes if outcome.episode_type is episode_type)
