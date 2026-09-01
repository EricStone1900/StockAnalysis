"""回测执行约束；只模拟成交可行性，不创建交易系统订单。"""

from __future__ import annotations

from datetime import date
from decimal import ROUND_DOWN, Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class BacktestSide(StrEnum):
    BUY = "BUY"
    SELL = "SELL"


class ExecutionStatus(StrEnum):
    EXECUTED = "EXECUTED"
    REJECTED = "REJECTED"


class BacktestExecutionInput(BaseModel):
    model_config = ConfigDict(frozen=True)

    security_id: str = Field(min_length=1)
    signal_date: date
    execution_date: date
    side: BacktestSide
    requested_quantity: Decimal = Field(gt=0)
    execution_price: Decimal | None = Field(default=None, gt=0)
    suspended: bool = False
    upper_limit_price: Decimal | None = Field(default=None, gt=0)
    lower_limit_price: Decimal | None = Field(default=None, gt=0)
    lot_size: int = Field(default=100, ge=1)

    @model_validator(mode="after")
    def validate_execution_context(self) -> BacktestExecutionInput:
        if self.execution_date <= self.signal_date:
            raise ValueError("execution_date must be later than signal_date")
        if (
            self.upper_limit_price is not None
            and self.lower_limit_price is not None
            and self.lower_limit_price >= self.upper_limit_price
        ):
            raise ValueError("lower_limit_price must be below upper_limit_price")
        return self


class BacktestExecutionResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    security_id: str
    execution_date: date
    side: BacktestSide
    status: ExecutionStatus
    requested_quantity: Decimal
    executed_quantity: Decimal
    execution_price: Decimal | None
    rejection_reason: str | None = None


def simulate_execution(order: BacktestExecutionInput) -> BacktestExecutionResult:
    """应用成交时点、停牌、涨跌停和最小交易单位规则。"""
    if order.suspended:
        return _rejected(order, "SUSPENDED")
    if order.execution_price is None:
        return _rejected(order, "MISSING_EXECUTION_PRICE")
    if (
        order.side is BacktestSide.BUY
        and order.upper_limit_price is not None
        and order.execution_price >= order.upper_limit_price
    ):
        return _rejected(order, "BUY_AT_LIMIT_UP")
    if (
        order.side is BacktestSide.SELL
        and order.lower_limit_price is not None
        and order.execution_price <= order.lower_limit_price
    ):
        return _rejected(order, "SELL_AT_LIMIT_DOWN")
    lots = (order.requested_quantity / Decimal(order.lot_size)).to_integral_value(rounding=ROUND_DOWN)
    executed_quantity = lots * Decimal(order.lot_size)
    if executed_quantity < order.lot_size:
        return _rejected(order, "BELOW_MINIMUM_LOT")
    return BacktestExecutionResult(
        security_id=order.security_id,
        execution_date=order.execution_date,
        side=order.side,
        status=ExecutionStatus.EXECUTED,
        requested_quantity=order.requested_quantity,
        executed_quantity=executed_quantity,
        execution_price=order.execution_price,
    )


def _rejected(order: BacktestExecutionInput, reason: str) -> BacktestExecutionResult:
    return BacktestExecutionResult(
        security_id=order.security_id,
        execution_date=order.execution_date,
        side=order.side,
        status=ExecutionStatus.REJECTED,
        requested_quantity=order.requested_quantity,
        executed_quantity=Decimal(0),
        execution_price=order.execution_price,
        rejection_reason=reason,
    )
