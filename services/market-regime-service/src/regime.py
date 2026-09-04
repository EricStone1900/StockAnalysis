"""确定性市场状态特征和快照。"""

from __future__ import annotations

from datetime import timedelta
from typing import Literal

from pydantic import AwareDatetime, BaseModel, Field


class RegimeDimensions(BaseModel):
    trend: float = Field(ge=-1, le=1)
    breadth: float = Field(ge=0, le=1)
    volatility: float = Field(ge=0, le=1)
    liquidity: float = Field(ge=0, le=1)


class RegimeDefinition(BaseModel):
    version: str
    stress_volatility: float = 0.8
    risk_on_score: float = 0.6
    risk_off_score: float = -0.3


class FeatureInput(BaseModel):
    as_of: AwareDatetime
    dimensions: RegimeDimensions
    data_version: str
    feature_version: str
    quality: Literal["PASS", "WARN", "FAIL"]
    evidence_ids: tuple[str, ...] = ()


class MarketRegimeSnapshot(BaseModel):
    snapshot_id: str
    as_of: AwareDatetime
    overall_regime: Literal["RISK_ON", "NEUTRAL", "RISK_OFF", "STRESS"]
    dimensions: RegimeDimensions
    data_version: str
    feature_version: str
    regime_definition_version: str
    freshness: Literal["FRESH", "STALE"]
    quality: Literal["PASS", "WARN", "FAIL"]
    evidence_ids: tuple[str, ...]


def classify(features: FeatureInput, definition: RegimeDefinition) -> MarketRegimeSnapshot:
    dimensions = features.dimensions
    if features.quality == "FAIL":
        raise ValueError("feature quality FAIL cannot publish a new regime")
    if dimensions.volatility >= definition.stress_volatility:
        regime: Literal["RISK_ON", "NEUTRAL", "RISK_OFF", "STRESS"] = "STRESS"
    elif dimensions.trend + dimensions.breadth - dimensions.volatility + dimensions.liquidity >= definition.risk_on_score:
        regime = "RISK_ON"
    elif dimensions.trend + dimensions.breadth - dimensions.volatility < definition.risk_off_score:
        regime = "RISK_OFF"
    else:
        regime = "NEUTRAL"
    return MarketRegimeSnapshot(
        snapshot_id=f"regime:{features.as_of.isoformat()}:{definition.version}", as_of=features.as_of,
        overall_regime=regime, dimensions=dimensions, data_version=features.data_version,
        feature_version=features.feature_version, regime_definition_version=definition.version,
        freshness="FRESH", quality=features.quality, evidence_ids=features.evidence_ids,
    )


class RegimeStateMachine:
    def __init__(self, minimum_duration_minutes: int = 30) -> None:
        self._minimum_duration = timedelta(minutes=minimum_duration_minutes)
        self._current: MarketRegimeSnapshot | None = None

    def evaluate(self, features: FeatureInput, definition: RegimeDefinition) -> MarketRegimeSnapshot:
        if features.quality == "FAIL":
            if self._current is None:
                raise ValueError("feature quality FAIL without previous snapshot")
            return self._current.model_copy(update={"freshness": "STALE", "quality": "FAIL"})
        candidate = classify(features, definition)
        if (
            self._current is not None
            and candidate.overall_regime != self._current.overall_regime
            and candidate.as_of - self._current.as_of < self._minimum_duration
            and candidate.overall_regime != "STRESS"
        ):
            return self._current
        self._current = candidate
        return candidate
