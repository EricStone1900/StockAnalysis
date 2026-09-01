"""版本化因子变换Adapter；不在Domain或跨服务DTO泄漏计算细节。"""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import UTC, date, datetime
from decimal import ROUND_HALF_EVEN, Decimal
from hashlib import sha256

from pydantic import BaseModel, ConfigDict, Field, field_validator

from quant_research.domain import DataQualityStatus

_PRECISION = Decimal("0.00000001")


class TransformSpec(BaseModel):
    model_config = ConfigDict(frozen=True)

    version: str = Field(min_length=1)
    cutoff_at: datetime
    winsorize_mad_multiplier: Decimal = Field(gt=0)
    industry_neutralize: bool = True
    market_cap_neutralize: bool = True
    standardize: bool = True

    @field_validator("cutoff_at")
    @classmethod
    def require_utc_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
            raise ValueError("cutoff_at must use UTC")
        return value


class RawFactorValue(BaseModel):
    model_config = ConfigDict(frozen=True)

    security_id: str = Field(min_length=1)
    trading_day: date
    factor_id: str = Field(min_length=1)
    value: Decimal | None
    industry: str | None
    market_cap: Decimal | None = Field(default=None, gt=0)
    available_at: datetime

    @field_validator("available_at")
    @classmethod
    def require_utc_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
            raise ValueError("available_at must use UTC")
        return value


class TransformedFactorValue(BaseModel):
    model_config = ConfigDict(frozen=True)

    security_id: str
    trading_day: date
    factor_id: str
    value: Decimal
    transform_version: str


class TransformedFactorMatrix(BaseModel):
    model_config = ConfigDict(frozen=True)

    data_version_id: str
    transform_version: str
    values: tuple[TransformedFactorValue, ...]
    quality_status: DataQualityStatus = DataQualityStatus.WARN
    canonical_content_hash: str


class VersionedFactorTransformAdapter:
    def apply(
        self,
        data_version_id: str,
        specification: TransformSpec,
        raw_values: tuple[RawFactorValue, ...],
    ) -> TransformedFactorMatrix:
        eligible = [
            item
            for item in raw_values
            if item.value is not None
            and item.available_at <= specification.cutoff_at
            and (not specification.industry_neutralize or item.industry is not None)
            and (not specification.market_cap_neutralize or item.market_cap is not None)
        ]
        groups: dict[tuple[date, str], list[RawFactorValue]] = defaultdict(list)
        for item in eligible:
            groups[(item.trading_day, item.factor_id)].append(item)
        transformed: list[TransformedFactorValue] = []
        for key in sorted(groups):
            transformed.extend(_transform_group(groups[key], specification))
        stable = tuple(sorted(transformed, key=lambda item: (item.security_id, item.trading_day, item.factor_id)))
        payload = {
            "dataVersionId": data_version_id,
            "transformVersion": specification.version,
            "qualityStatus": DataQualityStatus.WARN.value,
            "values": [
                {
                    "securityId": item.security_id,
                    "tradingDay": item.trading_day.isoformat(),
                    "factorId": item.factor_id,
                    "value": format(item.value, "f"),
                }
                for item in stable
            ],
        }
        canonical = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
        return TransformedFactorMatrix(
            data_version_id=data_version_id,
            transform_version=specification.version,
            values=stable,
            canonical_content_hash=sha256(canonical.encode("utf-8")).hexdigest(),
        )


def _transform_group(values: list[RawFactorValue], specification: TransformSpec) -> list[TransformedFactorValue]:
    ordered = sorted(values, key=lambda item: item.security_id)
    clipped = _winsorize([item.value for item in ordered if item.value is not None], specification.winsorize_mad_multiplier)
    residuals = dict(zip((item.security_id for item in ordered), clipped, strict=True))
    if specification.industry_neutralize:
        by_industry: dict[str, list[str]] = defaultdict(list)
        for item in ordered:
            if item.industry is not None:
                by_industry[item.industry].append(item.security_id)
        for identifiers in by_industry.values():
            average = _mean([residuals[security_id] for security_id in identifiers])
            for security_id in identifiers:
                residuals[security_id] -= average
    if specification.market_cap_neutralize:
        caps = [item.market_cap for item in ordered if item.market_cap is not None]
        cap_mean = _mean(caps)
        centered_caps = {item.security_id: item.market_cap - cap_mean for item in ordered if item.market_cap is not None}
        denominator = sum((value * value for value in centered_caps.values()), Decimal(0))
        if denominator != 0:
            numerator = sum((centered_caps[item.security_id] * residuals[item.security_id] for item in ordered), Decimal(0))
            beta = numerator / denominator
            for security_id, cap in centered_caps.items():
                residuals[security_id] -= beta * cap
    normalized = _standardize(residuals) if specification.standardize else residuals
    return [
        TransformedFactorValue(
            security_id=item.security_id,
            trading_day=item.trading_day,
            factor_id=item.factor_id,
            value=normalized[item.security_id].quantize(_PRECISION, rounding=ROUND_HALF_EVEN),
            transform_version=specification.version,
        )
        for item in ordered
    ]


def _winsorize(values: list[Decimal], multiplier: Decimal) -> list[Decimal]:
    median = _median(values)
    mad = _median([abs(value - median) for value in values])
    if mad == 0:
        return values
    lower, upper = median - multiplier * mad, median + multiplier * mad
    return [min(max(value, lower), upper) for value in values]


def _standardize(values: dict[str, Decimal]) -> dict[str, Decimal]:
    average = _mean(list(values.values()))
    variance = _mean([(value - average) ** 2 for value in values.values()])
    if variance == 0:
        return {security_id: Decimal(0) for security_id in values}
    deviation = variance.sqrt()
    return {security_id: (value - average) / deviation for security_id, value in values.items()}


def _mean(values: list[Decimal]) -> Decimal:
    return sum(values, Decimal(0)) / Decimal(len(values))


def _median(values: list[Decimal]) -> Decimal:
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / Decimal(2)
