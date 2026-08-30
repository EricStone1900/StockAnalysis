from datetime import date

from market_data.baostock_worker import BaoStockWorkerRequest, BaoStockWorkerResult
from market_data.worker_executor import FakeWorkerExecutor


def test_fake_worker_executor_delegates_request() -> None:
    executor = FakeWorkerExecutor(lambda request: BaoStockWorkerResult(ok=True, rows=({"code": request.code},)))
    result = executor.execute(BaoStockWorkerRequest(code="sh.600000", start=date(2026, 1, 1), end=date(2026, 1, 1)))
    assert result.ok is True
    assert result.rows[0]["code"] == "sh.600000"
