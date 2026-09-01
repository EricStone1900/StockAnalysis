from datetime import date
from decimal import Decimal

from quant_research.adapters.factor_engine import DailyPriceBar, FixturePriceFactorAdapter
from quant_research.domain import SuspensionMaskEntry


def bars() -> tuple[DailyPriceBar, ...]:
    return (
        DailyPriceBar(security_id="sh600000", trading_day=date(2020, 1, 1), close=Decimal(10), turnover=Decimal(100)),
        DailyPriceBar(security_id="sh600000", trading_day=date(2020, 1, 2), close=Decimal(11), turnover=Decimal(120)),
        DailyPriceBar(security_id="sh600000", trading_day=date(2020, 1, 3), close=Decimal(12), turnover=Decimal(150)),
        DailyPriceBar(security_id="sz000001", trading_day=date(2020, 1, 1), close=Decimal(20), turnover=Decimal(200)),
        DailyPriceBar(security_id="sz000001", trading_day=date(2020, 1, 2), close=Decimal(18), turnover=Decimal(190)),
        DailyPriceBar(security_id="sz000001", trading_day=date(2020, 1, 3), close=Decimal(21), turnover=Decimal(210)),
    )


def test_price_factors_are_stable_sorted_and_fixed_precision() -> None:
    adapter = FixturePriceFactorAdapter()
    first = adapter.calculate("cn-a-fixture-v1", bars(), ())
    second = adapter.calculate("cn-a-fixture-v1", tuple(reversed(bars())), ())

    sh_observations = [item for item in first.observations if item.security_id == "sh600000"]
    assert [(item.security_id, item.trading_day, item.factor_id) for item in first.observations] == sorted(
        (item.security_id, item.trading_day, item.factor_id) for item in first.observations
    )
    assert {item.factor_id for item in sh_observations} == {
        "price.momentum.2d",
        "price.volatility.2d",
        "liquidity.average-turnover.3d",
    }
    assert next(item.value for item in sh_observations if item.factor_id == "price.momentum.2d") == Decimal("0.20000000")
    assert first.canonical_content_hash == second.canonical_content_hash


def test_suspension_mask_excludes_current_day_and_its_price_lookback_window() -> None:
    result = FixturePriceFactorAdapter().calculate(
        "cn-a-fixture-v1",
        bars(),
        (SuspensionMaskEntry(security_id="sh600000", trading_day=date(2020, 1, 2)),),
    )

    assert all(item.security_id != "sh600000" for item in result.observations)
    assert {item.factor_id for item in result.observations} == {
        "price.momentum.2d",
        "price.volatility.2d",
        "liquidity.average-turnover.3d",
    }
