from collections.abc import Iterable
from datetime import date
from enum import StrEnum
from hashlib import sha256
from typing import Protocol

from pydantic import BaseModel, Field

from .domain import SecurityId


class StatusGap(Protocol):
    security_id: SecurityId
    trading_day: date


class StatusBatchState(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


class StatusBatch(BaseModel):
    batch_id: str
    ordinal: int = Field(ge=0)
    gap_count: int = Field(ge=1)
    first_key: str
    last_key: str
    state: StatusBatchState = StatusBatchState.PENDING


def plan_status_batches(
    gaps: Iterable[StatusGap], batch_size: int, *, identity_namespace: str = ""
) -> tuple[StatusBatch, ...]:
    """按稳定证券日顺序切分；命名空间隔离不同处理策略的批次身份。"""
    if batch_size < 1:
        raise ValueError("batch_size must be positive")
    ordered = sorted(gaps, key=_gap_key)
    batches: list[StatusBatch] = []
    for ordinal, start in enumerate(range(0, len(ordered), batch_size)):
        items = ordered[start : start + batch_size]
        first_key, last_key = _gap_key(items[0]), _gap_key(items[-1])
        identity_input = f"{ordinal}:{first_key}:{last_key}:{len(items)}"
        if identity_namespace:
            identity_input = f"{identity_namespace}:{identity_input}"
        identity = sha256(identity_input.encode()).hexdigest()
        batches.append(
            StatusBatch(
                batch_id=identity,
                ordinal=ordinal,
                gap_count=len(items),
                first_key=first_key,
                last_key=last_key,
            )
        )
    return tuple(batches)


def _gap_key(gap: StatusGap) -> str:
    return f"{gap.security_id.exchange}:{gap.security_id.symbol}:{gap.trading_day.isoformat()}"
