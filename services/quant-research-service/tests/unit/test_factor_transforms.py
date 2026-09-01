from datetime import UTC, date, datetime, timedelta, timezone
from decimal import Decimal

import pytest

from quant_research.adapters.factor_transforms import (
    RawFactorValue,
    TransformSpec,
    VersionedFactorTransformAdapter,
)


def specification() -> TransformSpec:
    return TransformSpec(
        version="winsorize-mad-industry-market-cap-zscore-v1",
        cutoff_at=datetime(2020, 1, 31, 8, tzinfo=UTC),
        winsorize_mad_multiplier=Decimal(3),
    )


def raw_values() -> tuple[RawFactorValue, ...]:
    values = (
        ("sh600000", Decimal(1), "bank", Decimal(10), datetime(2020, 1, 30, tzinfo=UTC)),
        ("sh600001", Decimal(2), "bank", Decimal(20), datetime(2020, 1, 30, tzinfo=UTC)),
        ("sz000001", Decimal(4), "technology", Decimal(10), datetime(2020, 1, 30, tzinfo=UTC)),
        ("sz000002", Decimal(100), "technology", Decimal(20), datetime(2020, 1, 30, tzinfo=UTC)),
        ("sz000003", None, "technology", Decimal(30), datetime(2020, 1, 30, tzinfo=UTC)),
        ("sz000004", Decimal(5), "technology", Decimal(40), datetime(2020, 1, 31, 9, tzinfo=UTC)),
    )
    return tuple(
        RawFactorValue(
            security_id=security_id,
            trading_day=date(2020, 1, 31),
            factor_id="price.momentum.2d",
            value=value,
            industry=industry,
            market_cap=market_cap,
            available_at=available_at,
        )
        for security_id, value, industry, market_cap, available_at in values
    )


def test_transform_filters_missing_and_future_data_and_is_deterministic() -> None:
    adapter = VersionedFactorTransformAdapter()
    first = adapter.apply("cn-a-fixture-v1", specification(), raw_values())
    second = adapter.apply("cn-a-fixture-v1", specification(), tuple(reversed(raw_values())))

    assert [item.security_id for item in first.values] == ["sh600000", "sh600001", "sz000001", "sz000002"]
    assert all(item.value.as_tuple().exponent == -8 for item in first.values)
    assert sum(item.value for item in first.values) == Decimal("0E-8")
    assert first.canonical_content_hash == second.canonical_content_hash


def test_transform_requires_utc_cutoff() -> None:
    values = specification().model_dump()
    values["cutoff_at"] = datetime(2020, 1, 31, 8, tzinfo=timezone(timedelta(hours=8)))
    with pytest.raises(ValueError, match="UTC"):
        TransformSpec.model_validate(values)
