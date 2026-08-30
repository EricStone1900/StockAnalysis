from decimal import Decimal
from enum import StrEnum

from .pit import DailyBar


class QualityStatus(StrEnum):
    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"


class QualityResult:
    def __init__(self, status: QualityStatus, reasons: list[str]) -> None:
        self.status = status
        self.reasons = reasons


def validate_daily_bars(bars: list[DailyBar]) -> QualityResult:
    reasons: list[str] = []
    keys: set[tuple[object, object]] = set()
    for bar in bars:
        key = (bar.security_id, bar.trading_day)
        if key in keys:
            reasons.append("duplicate_bar")
        keys.add(key)
        if min(bar.open, bar.high, bar.low, bar.close, bar.volume, bar.amount) < Decimal(0):
            reasons.append("negative_value")
        if not bar.low <= min(bar.open, bar.close) <= max(bar.open, bar.close) <= bar.high:
            reasons.append("invalid_ohlc_range")
    return QualityResult(QualityStatus.FAIL if reasons else QualityStatus.PASS, reasons)
