"""BaoStock 隔离 worker 的进程间契约。"""

from datetime import date

from pydantic import BaseModel, Field


class BaoStockWorkerRequest(BaseModel):
    code: str = Field(min_length=1)
    start: date
    end: date


class BaoStockWorkerResult(BaseModel):
    ok: bool
    rows: tuple[dict[str, str], ...] = ()
    error: str | None = None


def execute_worker(request: BaoStockWorkerRequest, client_factory: object) -> BaoStockWorkerResult:
    """在隔离进程中执行一次供应商查询；不返回登录凭证或完整异常堆栈。"""
    client = client_factory()  # type: ignore[operator]
    try:
        client.login()
        rows = client.query_history(request.code, request.start, request.end)
        return BaoStockWorkerResult(ok=True, rows=tuple(rows))
    except Exception as error:  # noqa: BLE001
        return BaoStockWorkerResult(ok=False, error=type(error).__name__)
    finally:
        try:
            client.logout()
        except Exception:  # noqa: BLE001 S110
            pass


def execute_worker_batch(requests: tuple[BaoStockWorkerRequest, ...], client_factory: object) -> tuple[BaoStockWorkerResult, ...]:
    client = client_factory()  # type: ignore[operator]
    try:
        client.login()
        results = []
        for request in requests:
            try:
                rows = tuple(client.query_history(request.code, request.start, request.end))
                results.append(BaoStockWorkerResult(ok=True, rows=rows))
            except Exception as error:  # noqa: BLE001
                results.append(BaoStockWorkerResult(ok=False, error=type(error).__name__))
        return tuple(results)
    except Exception as error:  # noqa: BLE001
        return tuple(BaoStockWorkerResult(ok=False, error=type(error).__name__) for _ in requests)
