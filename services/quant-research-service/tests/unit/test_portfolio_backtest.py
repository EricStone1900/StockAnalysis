from datetime import date
from decimal import Decimal

import pytest

from quant_research.backtest import BacktestExecutionInput, BacktestSide
from quant_research.cost_model import CostModelDefinition
from quant_research.portfolio_backtest import RoundTripTrade, run_portfolio_backtest


def execution(side: BacktestSide, signal: date, execution_day: date, price: str, **changes: object) -> BacktestExecutionInput:
    values: dict[str, object] = {
        "security_id": "sh600000",
        "signal_date": signal,
        "execution_date": execution_day,
        "side": side,
        "requested_quantity": Decimal(250),
        "execution_price": Decimal(price),
        "upper_limit_price": Decimal(12),
        "lower_limit_price": Decimal(8),
    }
    values.update(changes)
    return BacktestExecutionInput.model_validate(values)


def costs() -> CostModelDefinition:
    return CostModelDefinition(
        version="cn-a-v1", commission_rate=Decimal("0.001"), stamp_tax_rate=Decimal("0.001"),
        slippage_bps=Decimal(0), minimum_commission=Decimal(0),
    )


def test_portfolio_backtest_separates_gross_and_after_cost_results() -> None:
    trade = RoundTripTrade(
        trade_id="trade-001",
        buy=execution(BacktestSide.BUY, date(2026, 1, 2), date(2026, 1, 3), "10"),
        sell=execution(BacktestSide.SELL, date(2026, 1, 3), date(2026, 1, 4), "11"),
    )
    report = run_portfolio_backtest((trade,), costs())
    assert report.gross.gross_pnl == Decimal("200.00000000")
    assert report.gross.transaction_cost == Decimal("0E-8")
    assert report.gross.gross_return == Decimal("0.10000000")
    assert report.after_cost.transaction_cost == Decimal("6.40000000")
    assert report.after_cost.net_pnl == Decimal("193.60000000")
    assert report.gross.mode == "GROSS"
    assert report.after_cost.mode == "AFTER_COST"


def test_rejected_round_trip_is_retained_without_pnl() -> None:
    trade = RoundTripTrade(
        trade_id="trade-002",
        buy=execution(BacktestSide.BUY, date(2026, 1, 2), date(2026, 1, 3), "10", suspended=True),
        sell=execution(BacktestSide.SELL, date(2026, 1, 3), date(2026, 1, 4), "11"),
    )
    report = run_portfolio_backtest((trade,), costs())
    assert report.gross.trade_count == 0
    assert report.gross.rejected_trade_count == 1
    assert report.trades[0].buy_result.rejection_reason == "SUSPENDED"

    with pytest.raises(ValueError, match="must match"):
        RoundTripTrade(
            trade_id="bad",
            buy=execution(BacktestSide.BUY, date(2026, 1, 2), date(2026, 1, 3), "10"),
            sell=execution(BacktestSide.SELL, date(2026, 1, 3), date(2026, 1, 4), "11").model_copy(
                update={"security_id": "sz000001"}
            ),
        )
