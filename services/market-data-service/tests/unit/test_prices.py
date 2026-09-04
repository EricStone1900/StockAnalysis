from datetime import date
from decimal import Decimal

import pytest
from fastapi import HTTPException

import main
from market_data.prices import PricePoint, VersionedPriceStore


def test_versioned_price_store_is_pit_keyed() -> None:
    store = VersionedPriceStore()
    point = PricePoint(security_id="SSE:600000", close=Decimal("12.34"), as_of=date(2026, 9, 4), data_version="v1")
    store.put(point)
    assert store.get("SSE:600000", "v1", date(2026, 9, 4)) == point
    assert store.get("SSE:600000", "v2", date(2026, 9, 4)) is None


def test_price_api_returns_404_when_versioned_price_is_missing() -> None:
    with pytest.raises(HTTPException) as error:
        main.get_price("SSE:600000", "v-missing", date(2026, 9, 4))
    assert error.value.status_code == 404
