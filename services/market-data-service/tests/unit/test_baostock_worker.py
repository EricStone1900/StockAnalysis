from datetime import date

import pytest
from pydantic import ValidationError

from market_data.baostock_worker import BaoStockWorkerRequest, BaoStockWorkerResult


def test_worker_contract_round_trips_request_and_result() -> None:
    request = BaoStockWorkerRequest(code="sh.600000", start=date(2026, 8, 28), end=date(2026, 8, 28))
    result = BaoStockWorkerResult(ok=True, rows=({"date": "2026-08-28", "tradestatus": "1"},))
    assert BaoStockWorkerRequest.model_validate_json(request.model_dump_json()) == request
    assert BaoStockWorkerResult.model_validate_json(result.model_dump_json()) == result


def test_worker_request_rejects_empty_code() -> None:
    with pytest.raises(ValidationError):
        BaoStockWorkerRequest(code="", start=date(2026, 8, 28), end=date(2026, 8, 28))
