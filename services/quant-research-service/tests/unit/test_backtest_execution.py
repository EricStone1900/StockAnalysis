from datetime import date
from decimal import Decimal

import pytest

from quant_research.backtest import (
    BacktestExecutionInput,
    BacktestSide,
    ExecutionStatus,
    simulate_execution,
)


def order(**changes: object) -> BacktestExecutionInput:
    values: dict[str, object] = {
        "security_id": "sh600000",
        "signal_date": date(2026, 1, 2),
        "execution_date": date(2026, 1, 5),
        "side": BacktestSide.BUY,
        "requested_quantity": Decimal(250),
        "execution_price": Decimal("10.00"),
        "upper_limit_price": Decimal("10.50"),
        "lower_limit_price": Decimal("9.50"),
    }
    values.update(changes)
    return BacktestExecutionInput.model_validate(values)


def test_execution_applies_lot_size_and_signal_delay() -> None:
    result = simulate_execution(order())
    assert result.status is ExecutionStatus.EXECUTED
    assert result.executed_quantity == Decimal(200)
    with pytest.raises(ValueError, match="later"):
        order(execution_date=date(2026, 1, 2))


@pytest.mark.parametrize(
    ("changes", "reason"),
    [
        ({"suspended": True}, "SUSPENDED"),
        ({"execution_price": None}, "MISSING_EXECUTION_PRICE"),
        ({"execution_price": Decimal("10.50")}, "BUY_AT_LIMIT_UP"),
        ({"side": BacktestSide.SELL, "execution_price": Decimal("9.50")}, "SELL_AT_LIMIT_DOWN"),
        ({"requested_quantity": Decimal(50)}, "BELOW_MINIMUM_LOT"),
    ],
)
def test_execution_rejects_non_executable_conditions(changes: dict[str, object], reason: str) -> None:
    result = simulate_execution(order(**changes))
    assert result.status is ExecutionStatus.REJECTED
    assert result.rejection_reason == reason
    assert result.executed_quantity == Decimal(0)
