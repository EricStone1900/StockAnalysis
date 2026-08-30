from pathlib import Path

import pytest

from market_data.fixture_adapter import load_securities


def test_lifecycle_fixture_contains_active_suspended_and_delisted() -> None:
    fixture = Path(__file__).parents[1] / "fixtures/lifecycle.csv"
    assert len(list(load_securities(fixture))) == 3


def test_missing_supplier_field_is_rejected(tmp_path: Path) -> None:
    fixture = tmp_path / "bad.csv"
    fixture.write_text("exchange,symbol,name\nSSE,600000,\n")
    with pytest.raises(ValueError, match="missing"):
        list(load_securities(fixture))
