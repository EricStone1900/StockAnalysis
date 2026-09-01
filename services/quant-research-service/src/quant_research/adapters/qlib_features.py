"""从已初始化的只读Qlib Provider读取价格因子所需的特征。"""

from __future__ import annotations

import math
from collections.abc import Callable, Sequence
from datetime import date
from decimal import Decimal
from typing import Any

from quant_research.adapters.factor_engine import DailyPriceBar

FeatureLoader = Callable[[Sequence[str], Sequence[str], str, str], Any]


class QlibPriceFeatureReader:
    """Qlib专有字段名只留在此Adapter；领域层只接收DailyPriceBar。"""

    def __init__(self, loader: FeatureLoader | None = None) -> None:
        self._loader = loader or _qlib_feature_loader

    def load_bars(
        self,
        instruments: Sequence[str],
        start_date: date,
        end_date: date,
    ) -> tuple[DailyPriceBar, ...]:
        frame = self._loader(instruments, ("$close", "$amount"), start_date.isoformat(), end_date.isoformat())
        bars: list[DailyPriceBar] = []
        for (instrument, timestamp), row in frame.iterrows():
            bars.append(
                DailyPriceBar(
                    security_id=str(instrument).lower(),
                    trading_day=timestamp.date(),
                    close=_finite_decimal(row["$close"], positive=True),
                    turnover=_finite_decimal(row["$amount"], positive=False),
                )
            )
        return tuple(sorted(bars, key=lambda item: (item.security_id, item.trading_day)))


def _qlib_feature_loader(
    instruments: Sequence[str], fields: Sequence[str], start_date: str, end_date: str
) -> Any:
    from qlib.data import D

    return D.features(list(instruments), list(fields), start_time=start_date, end_time=end_date, freq="day")


def _finite_decimal(value: Any, *, positive: bool) -> Decimal | None:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(numeric) or (numeric <= 0 if positive else numeric < 0):
        return None
    return Decimal(str(value))
