from datetime import date
from decimal import Decimal

import pandas as pd

from quant_research.adapters.factor_engine import FixturePriceFactorAdapter
from quant_research.adapters.qlib_features import QlibPriceFeatureReader


def test_reader_preserves_nonfinite_qlib_prices_as_missing_and_normalizes_symbols() -> None:
    index = pd.MultiIndex.from_tuples(
        [("SH600000", pd.Timestamp("2020-01-01")), ("SH600000", pd.Timestamp("2020-01-02")), ("SH600000", pd.Timestamp("2020-01-03"))],
        names=("instrument", "datetime"),
    )
    frame = pd.DataFrame({"$close": [10.0, float("nan"), 12.0], "$amount": [100.0, 110.0, 120.0]}, index=index)
    reader = QlibPriceFeatureReader(lambda *_: frame)

    bars = reader.load_bars(("SH600000",), date(2020, 1, 1), date(2020, 1, 3))

    assert [item.security_id for item in bars] == ["sh600000", "sh600000", "sh600000"]
    assert bars[1].close is None
    assert bars[0].turnover == Decimal("100.0")
    assert FixturePriceFactorAdapter().calculate("fixture", bars, ()).observations == ()
