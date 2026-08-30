import json
import socket
from collections import defaultdict
from collections.abc import Callable, Iterable
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeoutError
from datetime import UTC, date, datetime
from hashlib import sha256
from threading import Lock
from time import sleep
from typing import Protocol

from pydantic import BaseModel, Field

from .baostock_worker import BaoStockWorkerRequest
from .domain import Exchange, SecurityId
from .worker_executor import WorkerExecutor


class BaoStockRow(BaseModel):
    date: date
    code: str
    tradestatus: str | None = None
    is_st: str | None = Field(default=None, alias="isST")


class BaoStockBatch(BaseModel):
    query_id: str
    observed_at: datetime
    rows: tuple[BaoStockRow, ...]

    def canonical_bytes(self) -> bytes:
        return json.dumps(self.model_dump(mode="json", by_alias=True), sort_keys=True, separators=(",", ":")).encode()


class BaoStockClient(Protocol):
    def login(self) -> None: ...

    def query_history(self, code: str, start: date, end: date) -> Iterable[dict[str, str]]: ...

    def logout(self) -> None: ...


class RetryPolicy(BaseModel):
    max_attempts: int = Field(default=3, ge=1, le=10)
    initial_backoff_seconds: float = Field(default=1.0, ge=0)
    min_interval_seconds: float = Field(default=0.2, ge=0)
    query_timeout_seconds: float = Field(default=30.0, gt=0)


_SOCKET_TIMEOUT_LOCK = Lock()


class BaoStockSdkClient:
    """BaoStock SDK 的窄封装，隔离第三方对象并保留其原始行字段。"""

    def __init__(self) -> None:
        try:
            import baostock as bs
        except ImportError as error:
            raise RuntimeError("baostock dependency is not installed") from error
        self._bs = bs

    def login(self) -> None:
        result = self._bs.login()
        if result.error_code != "0":
            raise RuntimeError(f"baostock login failed: {result.error_msg}")

    def query_history(self, code: str, start: date, end: date) -> Iterable[dict[str, str]]:
        result = self._bs.query_history_k_data_plus(
            code,
            "date,code,tradestatus,isST",
            start_date=start.isoformat(),
            end_date=end.isoformat(),
            frequency="d",
            adjustflag="3",
        )
        if result.error_code != "0":
            raise RuntimeError(f"baostock query failed: {result.error_msg}")
        rows: list[dict[str, str]] = []
        while result.next():
            rows.append(dict(zip(result.fields, result.get_row_data(), strict=True)))
        return rows

    def logout(self) -> None:
        self._bs.logout()


def baostock_code(security_id: SecurityId) -> str:
    prefixes = {Exchange.SSE: "sh", Exchange.SZSE: "sz"}
    if security_id.exchange not in prefixes:
        raise ValueError(f"baostock does not support exchange: {security_id.exchange}")
    return f"{prefixes[security_id.exchange]}.{security_id.symbol}"


def security_id_from_baostock(code: str) -> SecurityId:
    try:
        prefix, symbol = code.lower().split(".", 1)
        exchange = {"sh": Exchange.SSE, "sz": Exchange.SZSE, "bj": Exchange.BSE}[prefix]
    except (KeyError, ValueError) as error:
        raise ValueError(f"unsupported baostock security code: {code}") from error
    return SecurityId(exchange=exchange, symbol=symbol)


def security_id_from_qlib(symbol: str) -> SecurityId:
    normalized = symbol.lower()
    prefixes = {"sh": Exchange.SSE, "sz": Exchange.SZSE, "bj": Exchange.BSE}
    if len(normalized) != 8 or normalized[:2] not in prefixes or not normalized[2:].isdigit():
        raise ValueError(f"unsupported qlib security symbol: {symbol}")
    return SecurityId(exchange=prefixes[normalized[:2]], symbol=normalized[2:])


class BaoStockTradingStatusAdapter:
    """仅获取交易状态与ST字段；调用者负责将原始批次不可变落盘。"""

    def __init__(
        self,
        client_factory: Callable[[], BaoStockClient],
        now: Callable[[], datetime] | None = None,
        retry_policy: RetryPolicy | None = None,
        wait: Callable[[float], None] = sleep,
        worker_executor: WorkerExecutor | None = None,
    ) -> None:
        self.client_factory = client_factory
        self.now = now or (lambda: datetime.now(UTC))
        self.retry_policy = retry_policy or RetryPolicy()
        self.wait = wait
        self.worker_executor = worker_executor

    def probe(self, security_id: SecurityId, day: date) -> BaoStockBatch:
        """最小能力探针。无有效字段、异常代码或未来时间均视为失败。"""
        batch = self.fetch(((security_id, day, day),))[0]
        if not batch.rows or any(row.tradestatus not in {"0", "1", None} for row in batch.rows):
            raise ValueError("baostock status capability probe failed")
        return batch

    def fetch(self, requests: Iterable[tuple[SecurityId, date, date]]) -> tuple[BaoStockBatch, ...]:
        if self.worker_executor is not None:
            return self._fetch_with_worker(requests)
        client = self.client_factory()
        batches: list[BaoStockBatch] = []
        self._login_with_timeout(client)
        try:
            for security_id, start, end in requests:
                if end < start:
                    raise ValueError("status request end must not be earlier than start")
                code = baostock_code(security_id)
                rows = self._query_with_retry(client, code, start, end)
                query_id = sha256(f"{code}:{start.isoformat()}:{end.isoformat()}".encode()).hexdigest()
                batches.append(BaoStockBatch(query_id=query_id, observed_at=self.now(), rows=rows))
        finally:
            client.logout()
        return tuple(batches)

    def _fetch_with_worker(self, requests: Iterable[tuple[SecurityId, date, date]]) -> tuple[BaoStockBatch, ...]:
        executor = self.worker_executor
        if executor is None:
            raise AssertionError("worker executor is required")
        batches: list[BaoStockBatch] = []
        request_items = tuple(requests)
        worker_requests = tuple(BaoStockWorkerRequest(code=baostock_code(security_id), start=start, end=end) for security_id, start, end in request_items)
        results = executor.execute_many(worker_requests)
        for (security_id, start, end), result in zip(request_items, results, strict=True):
            if end < start:
                raise ValueError("status request end must not be earlier than start")
            if not result.ok:
                raise RuntimeError(f"baostock worker failed: {result.error or 'unknown error'}")
            query_id = sha256(f"{baostock_code(security_id)}:{start.isoformat()}:{end.isoformat()}".encode()).hexdigest()
            batches.append(BaoStockBatch(query_id=query_id, observed_at=self.now(), rows=tuple(BaoStockRow.model_validate(row) for row in result.rows)))
        return tuple(batches)

    def _login_with_timeout(self, client: BaoStockClient) -> None:
        with _SOCKET_TIMEOUT_LOCK:
            previous = socket.getdefaulttimeout()
            socket.setdefaulttimeout(self.retry_policy.query_timeout_seconds)
            try:
                executor = ThreadPoolExecutor(max_workers=1)
                future = executor.submit(client.login)
                try:
                    future.result(timeout=self.retry_policy.query_timeout_seconds)
                except FutureTimeoutError as error:
                    future.cancel()
                    raise TimeoutError("baostock login timed out") from error
                finally:
                    executor.shutdown(wait=False, cancel_futures=True)
            finally:
                socket.setdefaulttimeout(previous)

    def _query_with_retry(
        self, client: BaoStockClient, code: str, start: date, end: date
    ) -> tuple[BaoStockRow, ...]:
        last_error: Exception | None = None
        for attempt in range(self.retry_policy.max_attempts):
            try:
                rows = tuple(BaoStockRow.model_validate(row) for row in self._query_with_timeout(client, code, start, end))
                if self.retry_policy.min_interval_seconds:
                    self.wait(self.retry_policy.min_interval_seconds)
                return rows
            except (OSError, RuntimeError, TimeoutError, ValueError) as error:
                last_error = error
                if attempt + 1 == self.retry_policy.max_attempts:
                    break
                self.wait(self.retry_policy.initial_backoff_seconds * (2**attempt))
        raise RuntimeError(f"baostock query failed after retries for {code}") from last_error

    def _query_with_timeout(
        self, client: BaoStockClient, code: str, start: date, end: date
    ) -> Iterable[dict[str, str]]:
        """BaoStock SDK不暴露超时参数；以进程级socket超时串行保护其网络调用。"""
        with _SOCKET_TIMEOUT_LOCK:
            previous = socket.getdefaulttimeout()
            socket.setdefaulttimeout(self.retry_policy.query_timeout_seconds)
            try:
                return client.query_history(code, start, end)
            finally:
                socket.setdefaulttimeout(previous)


def requests_for_days(days: Iterable[tuple[SecurityId, date]]) -> tuple[tuple[SecurityId, date, date], ...]:
    """按证券合并连续日期，减少供应商调用；不扩大请求范围。"""
    grouped: dict[SecurityId, list[date]] = defaultdict(list)
    for security_id, day in days:
        grouped[security_id].append(day)
    requests: list[tuple[SecurityId, date, date]] = []
    for security_id, dates in grouped.items():
        ordered = sorted(set(dates))
        if not ordered:
            continue
        start = end = ordered[0]
        for day in ordered[1:]:
            if (day - end).days == 1:
                end = day
                continue
            requests.append((security_id, start, end))
            start = end = day
        requests.append((security_id, start, end))
    return tuple(requests)
