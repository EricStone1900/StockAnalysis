"""最小组合回测汇总；不连接交易执行系统。"""

from __future__ import annotations

import json
from decimal import ROUND_HALF_EVEN, Decimal
from hashlib import sha256

from pydantic import BaseModel, ConfigDict, Field, model_validator

from quant_research.backtest import (
    BacktestExecutionInput,
    BacktestExecutionResult,
    BacktestSide,
    ExecutionStatus,
    simulate_execution,
)
from quant_research.cost_model import CostModelDefinition, estimate_trade_cost

_PRECISION = Decimal("0.00000001")


class RoundTripTrade(BaseModel):
    model_config = ConfigDict(frozen=True)

    trade_id: str = Field(min_length=1)
    buy: BacktestExecutionInput
    sell: BacktestExecutionInput

    @model_validator(mode="after")
    def validate_round_trip(self) -> RoundTripTrade:
        if self.buy.security_id != self.sell.security_id:
            raise ValueError("round-trip buy and sell securities must match")
        if self.buy.side is not BacktestSide.BUY or self.sell.side is not BacktestSide.SELL:
            raise ValueError("round-trip must contain BUY then SELL")
        if self.sell.execution_date <= self.buy.execution_date:
            raise ValueError("sell execution must be later than buy execution")
        if self.buy.requested_quantity != self.sell.requested_quantity:
            raise ValueError("round-trip quantities must match")
        return self


class BacktestTradeResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    trade_id: str
    buy_result: BacktestExecutionResult
    sell_result: BacktestExecutionResult
    gross_pnl: Decimal
    transaction_cost: Decimal
    net_pnl: Decimal


class BacktestSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    mode: str
    cost_model_version: str
    trade_count: int = Field(ge=0)
    rejected_trade_count: int = Field(ge=0)
    gross_pnl: Decimal
    transaction_cost: Decimal
    net_pnl: Decimal
    gross_return: Decimal
    net_return: Decimal
    canonical_content_hash: str = Field(min_length=64, max_length=64)
    eligibility: str = "RESEARCH_ONLY"


class PortfolioBacktestReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    gross: BacktestSummary
    after_cost: BacktestSummary
    trades: tuple[BacktestTradeResult, ...]


def run_portfolio_backtest(
    trades: tuple[RoundTripTrade, ...], cost_model: CostModelDefinition
) -> PortfolioBacktestReport:
    """模拟往返持仓并分开输出毛收益与成本后收益。"""
    if not trades:
        raise ValueError("portfolio backtest requires trades")
    results: list[BacktestTradeResult] = []
    for trade in trades:
        buy_result = simulate_execution(trade.buy)
        sell_result = simulate_execution(trade.sell)
        if buy_result.status is ExecutionStatus.EXECUTED and sell_result.status is ExecutionStatus.EXECUTED:
            assert buy_result.execution_price is not None and sell_result.execution_price is not None
            assert buy_result.executed_quantity == sell_result.executed_quantity
            gross_pnl = buy_result.executed_quantity * (sell_result.execution_price - buy_result.execution_price)
            costs = estimate_trade_cost(
                cost_model,
                buy_notional=buy_result.executed_quantity * buy_result.execution_price,
                sell_notional=sell_result.executed_quantity * sell_result.execution_price,
            ).total_cost
        else:
            gross_pnl = Decimal(0)
            costs = Decimal(0)
        results.append(
            BacktestTradeResult(
                trade_id=trade.trade_id,
                buy_result=buy_result,
                sell_result=sell_result,
                gross_pnl=_quantize(gross_pnl),
                transaction_cost=_quantize(costs),
                net_pnl=_quantize(gross_pnl - costs),
            )
        )
    executed = [
        result
        for result in results
        if result.buy_result.status is ExecutionStatus.EXECUTED
        and result.sell_result.status is ExecutionStatus.EXECUTED
    ]
    gross_pnl = _quantize(sum((result.gross_pnl for result in executed), Decimal(0)))
    transaction_cost = _quantize(sum((result.transaction_cost for result in executed), Decimal(0)))
    invested = _quantize(
        sum(
            (
                result.buy_result.executed_quantity * trade.buy.execution_price
                for result, trade in zip(results, trades, strict=True)
                if result.buy_result.status is ExecutionStatus.EXECUTED
                and result.sell_result.status is ExecutionStatus.EXECUTED
                and trade.buy.execution_price is not None
            ),
            Decimal(0),
        )
    )
    gross = _summary("GROSS", "NONE", results, gross_pnl, Decimal(0), gross_pnl, invested)
    after_cost = _summary("AFTER_COST", cost_model.version, results, gross_pnl, transaction_cost, gross_pnl - transaction_cost, invested)
    return PortfolioBacktestReport(gross=gross, after_cost=after_cost, trades=tuple(results))


def _summary(mode: str, cost_version: str, results: list[BacktestTradeResult], gross_pnl: Decimal, costs: Decimal, net_pnl: Decimal, invested: Decimal) -> BacktestSummary:
    if invested == 0:
        gross_return = Decimal(0)
        net_return = Decimal(0)
    else:
        gross_return = _quantize(gross_pnl / invested)
        net_return = _quantize(net_pnl / invested)
    trade_count = sum(
        result.buy_result.status is ExecutionStatus.EXECUTED
        and result.sell_result.status is ExecutionStatus.EXECUTED
        for result in results
    )
    rejected_trade_count = len(results) - trade_count
    payload = {
        "mode": mode, "costModelVersion": cost_version,
        "tradeCount": trade_count,
        "rejectedTradeCount": rejected_trade_count,
        "grossPnl": format(gross_pnl, "f"), "transactionCost": format(costs, "f"),
        "netPnl": format(net_pnl, "f"), "grossReturn": format(gross_return, "f"),
        "netReturn": format(net_return, "f"),
    }
    canonical = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return BacktestSummary(
        mode=mode, cost_model_version=cost_version,
        trade_count=trade_count, rejected_trade_count=rejected_trade_count,
        gross_pnl=gross_pnl, transaction_cost=costs, net_pnl=net_pnl,
        gross_return=gross_return, net_return=net_return,
        canonical_content_hash=sha256(canonical.encode("utf-8")).hexdigest(),
    )


def _quantize(value: Decimal) -> Decimal:
    return value.quantize(_PRECISION, rounding=ROUND_HALF_EVEN)
