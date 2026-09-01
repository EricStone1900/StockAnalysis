"""首版交易成本模型；成本后结果与无成本结果分开保存。"""

from __future__ import annotations

import json
from decimal import ROUND_HALF_EVEN, Decimal
from enum import StrEnum
from hashlib import sha256

from pydantic import BaseModel, ConfigDict, Field

from quant_research.models import EvaluationReport

_PRECISION = Decimal("0.00000001")
_BPS = Decimal(10000)


class TradeSide(StrEnum):
    BUY = "BUY"
    SELL = "SELL"


class CostModelDefinition(BaseModel):
    model_config = ConfigDict(frozen=True)

    version: str = Field(min_length=1)
    commission_rate: Decimal = Field(ge=0)
    stamp_tax_rate: Decimal = Field(ge=0)
    slippage_bps: Decimal = Field(ge=0)
    minimum_commission: Decimal = Field(ge=0)


class TradeCostEstimate(BaseModel):
    model_config = ConfigDict(frozen=True)

    cost_model_version: str
    buy_notional: Decimal
    sell_notional: Decimal
    commission: Decimal
    stamp_tax: Decimal
    slippage: Decimal
    total_cost: Decimal


class CostEvaluationObservation(BaseModel):
    model_config = ConfigDict(frozen=True)

    gross_return: Decimal
    buy_notional: Decimal = Field(ge=0)
    sell_notional: Decimal = Field(ge=0)


class CostAdjustedEvaluationReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    source_report_id: str
    cost_model_version: str
    observation_count: int = Field(ge=1)
    mean_gross_return: Decimal
    mean_transaction_cost: Decimal
    mean_net_return: Decimal
    canonical_content_hash: str = Field(min_length=64, max_length=64)
    eligibility: str = "RESEARCH_ONLY"


def estimate_trade_cost(
    model: CostModelDefinition,
    *,
    buy_notional: Decimal,
    sell_notional: Decimal,
) -> TradeCostEstimate:
    """按买卖名义金额估算佣金、卖出印花税和双边滑点。"""
    if buy_notional < 0 or sell_notional < 0:
        raise ValueError("trade notional cannot be negative")
    commission = _commission(model, buy_notional) + _commission(model, sell_notional)
    stamp_tax = sell_notional * model.stamp_tax_rate
    slippage = (buy_notional + sell_notional) * model.slippage_bps / _BPS
    return TradeCostEstimate(
        cost_model_version=model.version,
        buy_notional=buy_notional,
        sell_notional=sell_notional,
        commission=_quantize(commission),
        stamp_tax=_quantize(stamp_tax),
        slippage=_quantize(slippage),
        total_cost=_quantize(commission + stamp_tax + slippage),
    )


def evaluate_cost_adjusted_returns(
    report: EvaluationReport,
    model: CostModelDefinition,
    observations: tuple[CostEvaluationObservation, ...],
) -> CostAdjustedEvaluationReport:
    """生成独立成本后报告；输入报告和无成本指标保持不变。"""
    if not observations:
        raise ValueError("cost evaluation requires observations")
    if report.prediction_count != len(observations):
        raise ValueError("cost observations must match the source report prediction count")
    estimates = tuple(
        estimate_trade_cost(model, buy_notional=item.buy_notional, sell_notional=item.sell_notional)
        for item in observations
    )
    gross = _mean([item.gross_return for item in observations])
    cost = _mean([item.total_cost for item in estimates])
    net = gross - cost
    payload = {
        "sourceReportId": report.report_id,
        "costModelVersion": model.version,
        "observationCount": len(observations),
        "meanGrossReturn": format(_quantize(gross), "f"),
        "meanTransactionCost": format(_quantize(cost), "f"),
        "meanNetReturn": format(_quantize(net), "f"),
    }
    canonical = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return CostAdjustedEvaluationReport(
        source_report_id=report.report_id,
        cost_model_version=model.version,
        observation_count=len(observations),
        mean_gross_return=_quantize(gross),
        mean_transaction_cost=_quantize(cost),
        mean_net_return=_quantize(net),
        canonical_content_hash=sha256(canonical.encode("utf-8")).hexdigest(),
    )


def _commission(model: CostModelDefinition, notional: Decimal) -> Decimal:
    if notional == 0:
        return Decimal(0)
    return max(notional * model.commission_rate, model.minimum_commission)


def _mean(values: list[Decimal]) -> Decimal:
    return sum(values, Decimal(0)) / Decimal(len(values))


def _quantize(value: Decimal) -> Decimal:
    return value.quantize(_PRECISION, rounding=ROUND_HALF_EVEN)
