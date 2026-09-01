"""首批价格类因子的Fixture Adapter；Qlib表达式接入只能扩展本模块。"""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import date
from decimal import ROUND_HALF_EVEN, Decimal
from hashlib import sha256
from math import sqrt

from pydantic import BaseModel, ConfigDict, Field, field_validator

from quant_research.domain import DataQualityStatus, SuspensionMaskEntry

_PRECISION = Decimal("0.00000001")


class DailyPriceBar(BaseModel):
    """已通过PIT截止时间过滤的日频输入；不代表对原始Artifact的写权限。"""

    model_config = ConfigDict(frozen=True)

    security_id: str = Field(min_length=1)
    trading_day: date
    close: Decimal | None = Field(default=None, gt=0)
    turnover: Decimal | None = Field(default=None, ge=0)


class FactorObservation(BaseModel):
    model_config = ConfigDict(frozen=True)

    security_id: str
    trading_day: date
    factor_id: str
    value: Decimal

    @field_validator("value")
    @classmethod
    def require_fixed_precision(cls, value: Decimal) -> Decimal:
        quantized = value.quantize(_PRECISION, rounding=ROUND_HALF_EVEN)
        if value != quantized:
            raise ValueError("factor values must use fixed 8-decimal precision")
        return quantized


class PriceFactorMatrix(BaseModel):
    model_config = ConfigDict(frozen=True)

    data_version_id: str
    observations: tuple[FactorObservation, ...]
    quality_status: DataQualityStatus = DataQualityStatus.WARN
    canonical_content_hash: str


def canonical_price_factor_matrix_hash(
    data_version_id: str,
    observations: tuple[FactorObservation, ...],
    quality_status: DataQualityStatus = DataQualityStatus.WARN,
) -> str:
    """跨平台验证矩阵内容的规范Hash；文件编码与运行时间不参与计算。"""
    stable = tuple(sorted(observations, key=lambda item: (item.security_id, item.trading_day, item.factor_id)))
    payload = {
        "dataVersionId": data_version_id,
        "qualityStatus": quality_status.value,
        "observations": [
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
    return sha256(canonical.encode("utf-8")).hexdigest()


class FixturePriceFactorAdapter:
    """确定性三日窗口实现，供S3测试与跨平台规范化验证使用。"""

    def calculate(
        self,
        data_version_id: str,
        bars: tuple[DailyPriceBar, ...],
        suspension_mask: tuple[SuspensionMaskEntry, ...],
    ) -> PriceFactorMatrix:
        masked = {(entry.security_id, entry.trading_day) for entry in suspension_mask}
        grouped: dict[str, list[DailyPriceBar]] = defaultdict(list)
        for bar in bars:
            grouped[bar.security_id].append(bar)
        observations: list[FactorObservation] = []
        for security_id in sorted(grouped):
            ordered = sorted(grouped[security_id], key=lambda item: item.trading_day)
            observations.extend(_calculate_security(ordered, masked))
        stable = tuple(sorted(observations, key=lambda item: (item.security_id, item.trading_day, item.factor_id)))
        return PriceFactorMatrix(
            data_version_id=data_version_id,
            observations=stable,
            canonical_content_hash=canonical_price_factor_matrix_hash(data_version_id, stable),
        )


def _calculate_security(
    bars: list[DailyPriceBar], masked: set[tuple[str, date]]
) -> list[FactorObservation]:
    result: list[FactorObservation] = []
    for index in range(2, len(bars)):
        window = bars[index - 2 : index + 1]
        if any(
            (bar.security_id, bar.trading_day) in masked or bar.close is None or bar.turnover is None
            for bar in window
        ):
            continue
        first, middle, current = window
        assert first.close is not None and first.turnover is not None
        assert middle.close is not None and middle.turnover is not None
        assert current.close is not None and current.turnover is not None
        first_return = middle.close / first.close - Decimal(1)
        second_return = current.close / middle.close - Decimal(1)
        volatility = Decimal(str(sqrt(float((first_return**2 + second_return**2) / Decimal(2))))).quantize(
            _PRECISION, rounding=ROUND_HALF_EVEN
        )
        momentum = (current.close / first.close - Decimal(1)).quantize(_PRECISION, rounding=ROUND_HALF_EVEN)
        liquidity = ((first.turnover + middle.turnover + current.turnover) / Decimal(3)).quantize(
            _PRECISION, rounding=ROUND_HALF_EVEN
        )
        for factor_id, value in (
            ("price.momentum.2d", momentum),
            ("price.volatility.2d", volatility),
            ("liquidity.average-turnover.3d", liquidity),
        ):
            result.append(
                FactorObservation(
                    security_id=current.security_id,
                    trading_day=current.trading_day,
                    factor_id=factor_id,
                    value=value,
                )
            )
    return result
