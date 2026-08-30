import logging
from collections.abc import Callable
from multiprocessing import Process, Queue
from typing import Any, Protocol, cast

from .baostock_worker import BaoStockWorkerRequest, BaoStockWorkerResult

logger = logging.getLogger(__name__)


class WorkerExecutor(Protocol):
    def execute(self, request: BaoStockWorkerRequest) -> BaoStockWorkerResult: ...

    def execute_many(self, requests: tuple[BaoStockWorkerRequest, ...]) -> tuple[BaoStockWorkerResult, ...]: ...


class FakeWorkerExecutor:
    def __init__(self, handler: Callable[[BaoStockWorkerRequest], BaoStockWorkerResult]) -> None:
        self.handler = handler

    def execute(self, request: BaoStockWorkerRequest) -> BaoStockWorkerResult:
        return self.handler(request)

    def execute_many(self, requests: tuple[BaoStockWorkerRequest, ...]) -> tuple[BaoStockWorkerResult, ...]:
        return tuple(self.handler(request) for request in requests)


class MultiprocessingWorkerExecutor:
    def __init__(self, timeout_seconds: float) -> None:
        self.timeout_seconds = timeout_seconds

    def execute(self, request: BaoStockWorkerRequest) -> BaoStockWorkerResult:
        return self._execute_requests((request,))[0]

    def execute_many(self, requests: tuple[BaoStockWorkerRequest, ...]) -> tuple[BaoStockWorkerResult, ...]:
        return self._execute_requests(requests)

    def _execute_requests(self, requests: tuple[BaoStockWorkerRequest, ...]) -> tuple[BaoStockWorkerResult, ...]:
        queue: Any = Queue(maxsize=1)
        process = Process(target=_run_baostock_worker, args=(requests, queue), daemon=True)
        process.start()
        process.join(self.timeout_seconds)
        if process.is_alive():
            logger.warning("baostock worker timed out; terminating child process")
            process.terminate()
            process.join(1)
            if process.is_alive():
                logger.error("baostock worker did not exit after termination")
            return tuple(BaoStockWorkerResult(ok=False, error="worker_timeout") for _ in requests)
        if queue.empty():
            return tuple(BaoStockWorkerResult(ok=False, error="worker_exited_without_result") for _ in requests)
        return cast(tuple[BaoStockWorkerResult, ...], queue.get())


def _run_baostock_worker(requests: tuple[BaoStockWorkerRequest, ...], queue: Any) -> None:
    from .baostock_status import BaoStockSdkClient
    from .baostock_worker import execute_worker_batch

    queue.put(execute_worker_batch(requests, BaoStockSdkClient))
