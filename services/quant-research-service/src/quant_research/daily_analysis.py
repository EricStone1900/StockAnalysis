"""每日量化分析运行与原子快照发布。"""

from __future__ import annotations

import json
from datetime import UTC, date, datetime
from decimal import Decimal
from enum import StrEnum
from hashlib import sha256
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field, model_validator

from quant_research.domain import ArtifactRef, DataQualityStatus


class DailyQuantRunStatus(StrEnum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    VALIDATING = "VALIDATING"
    READY = "READY"
    FAILED = "FAILED"


class DailyAnalysisInput(BaseModel):
    model_config = ConfigDict(frozen=True)

    data_version_id: str = Field(min_length=1)
    universe_version: str = Field(min_length=1)
    factor_set_version: str = Field(min_length=1)
    model_version: str = Field(min_length=1)
    portfolio_snapshot: ArtifactRef | None = None
    quality_status: DataQualityStatus

    @model_validator(mode="after")
    def reject_failed_input(self) -> DailyAnalysisInput:
        if self.quality_status is DataQualityStatus.FAIL:
            raise ValueError("FAIL input cannot create a daily analysis")
        return self


class DailyCandidateAnalysis(BaseModel):
    model_config = ConfigDict(frozen=True)

    security_id: str = Field(min_length=1)
    rank: int = Field(ge=1)
    score: Decimal
    signals: tuple[str, ...] = ()


class DailyHoldingAnalysis(BaseModel):
    model_config = ConfigDict(frozen=True)

    security_id: str = Field(min_length=1)
    target_weight: Decimal = Field(ge=0, le=1)
    in_candidate_universe: bool
    signals: tuple[str, ...] = ()


class DailyQualitySummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: DataQualityStatus
    excluded_count: int = Field(ge=0)
    warning_reasons: tuple[str, ...] = ()


class DailyAnalysisSnapshot(BaseModel):
    """所有校验通过后一次性发布的不可变每日分析结果。"""

    model_config = ConfigDict(frozen=True)

    snapshot_id: str = Field(min_length=1)
    run_id: str = Field(min_length=1)
    as_of_date: date
    input: DailyAnalysisInput
    candidates: tuple[DailyCandidateAnalysis, ...]
    holdings: tuple[DailyHoldingAnalysis, ...]
    quality: DailyQualitySummary
    evidence_ids: tuple[str, ...] = ()
    canonical_content_hash: str = Field(min_length=64, max_length=64)
    is_stale: bool = False
    valid_until: datetime | None = None

    @model_validator(mode="after")
    def validate_snapshot(self) -> DailyAnalysisSnapshot:
        if self.quality.status is DataQualityStatus.FAIL:
            raise ValueError("FAIL quality cannot publish a snapshot")
        if tuple(sorted(self.candidates, key=lambda item: item.security_id)) != self.candidates:
            raise ValueError("candidates must be sorted by security_id")
        if tuple(sorted(self.holdings, key=lambda item: item.security_id)) != self.holdings:
            raise ValueError("holdings must be sorted by security_id")
        return self


class DailyQuantRun(BaseModel):
    model_config = ConfigDict(frozen=True)

    run_id: str = Field(min_length=1)
    status: DailyQuantRunStatus
    as_of_date: date
    input: DailyAnalysisInput
    snapshot_id: str | None = None
    failure_reason: str | None = None
    started_at: datetime
    completed_at: datetime | None = None

    @model_validator(mode="after")
    def validate_state(self) -> DailyQuantRun:
        for value in (self.started_at, self.completed_at):
            if value is not None and (value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value)):
                raise ValueError("run timestamps must use UTC")
        if self.status is DailyQuantRunStatus.READY and self.snapshot_id is None:
            raise ValueError("READY run requires snapshot_id")
        if self.status is DailyQuantRunStatus.FAILED and not self.failure_reason:
            raise ValueError("FAILED run requires failure_reason")
        return self


class DailyAnalysisRepository(Protocol):
    def publish_atomically(self, snapshot: DailyAnalysisSnapshot) -> None: ...
    def get(self, snapshot_id: str) -> DailyAnalysisSnapshot | None: ...
    def latest_ready(self) -> DailyAnalysisSnapshot | None: ...


class DailyAnalysisEventPublisher(Protocol):
    def publish(self, subject: str, payload: dict[str, object]) -> None: ...


class InMemoryDailyAnalysisRepository:
    """Fixture/本地验证仓储；发布操作只有完整快照才写入。"""

    def __init__(self) -> None:
        self._snapshots: dict[str, str] = {}
        self._latest_id: str | None = None

    def publish_atomically(self, snapshot: DailyAnalysisSnapshot) -> None:
        payload = _canonical_json(snapshot)
        existing = self._snapshots.get(snapshot.snapshot_id)
        if existing is not None and existing != payload:
            raise ValueError("snapshot id already contains different content")
        self._snapshots[snapshot.snapshot_id] = payload
        self._latest_id = snapshot.snapshot_id

    def get(self, snapshot_id: str) -> DailyAnalysisSnapshot | None:
        payload = self._snapshots.get(snapshot_id)
        return None if payload is None else DailyAnalysisSnapshot.model_validate_json(payload)

    def latest_ready(self) -> DailyAnalysisSnapshot | None:
        return None if self._latest_id is None else self.get(self._latest_id)


class DailyAnalysisService:
    def __init__(self, repository: DailyAnalysisRepository, events: DailyAnalysisEventPublisher | None = None) -> None:
        self._repository = repository
        self._events = events
        self._runs: dict[str, DailyQuantRun] = {}

    def start(self, run_id: str, as_of_date: date, input: DailyAnalysisInput, now: datetime) -> DailyQuantRun:
        _require_utc(now)
        existing = self._runs.get(run_id)
        if existing is not None:
            if existing.input != input or existing.as_of_date != as_of_date:
                raise ValueError("run id already contains different input")
            return existing
        run = DailyQuantRun(run_id=run_id, status=DailyQuantRunStatus.RUNNING, as_of_date=as_of_date, input=input, started_at=now)
        self._runs[run_id] = run
        return run

    def publish(
        self,
        run_id: str,
        candidates: tuple[DailyCandidateAnalysis, ...],
        holdings: tuple[DailyHoldingAnalysis, ...],
        quality: DailyQualitySummary,
        evidence_ids: tuple[str, ...],
        now: datetime,
    ) -> DailyAnalysisSnapshot:
        _require_utc(now)
        run = self._runs.get(run_id)
        if run is None:
            raise ValueError("unknown daily analysis run")
        if run.status not in {DailyQuantRunStatus.RUNNING, DailyQuantRunStatus.VALIDATING}:
            raise ValueError("run is not publishable")
        self._runs[run_id] = run.model_copy(update={"status": DailyQuantRunStatus.VALIDATING})
        ordered_candidates = tuple(sorted(candidates, key=lambda item: item.security_id))
        ordered_holdings = tuple(sorted(holdings, key=lambda item: item.security_id))
        snapshot_id = f"daily-analysis-{run_id}"
        snapshot = DailyAnalysisSnapshot(
            snapshot_id=snapshot_id, run_id=run_id, as_of_date=run.as_of_date, input=run.input,
            candidates=ordered_candidates, holdings=ordered_holdings, quality=quality,
            evidence_ids=tuple(sorted(set(evidence_ids))), canonical_content_hash="0" * 64,
        )
        snapshot = snapshot.model_copy(update={"canonical_content_hash": _snapshot_hash(snapshot)})
        self._repository.publish_atomically(snapshot)
        self._runs[run_id] = run.model_copy(update={"status": DailyQuantRunStatus.READY, "snapshot_id": snapshot_id, "completed_at": now})
        if self._events is not None:
            self._events.publish("stock.quant.daily-analysis.published.v1", {"snapshotId": snapshot_id, "runId": run_id, "contentHash": snapshot.canonical_content_hash})
        return snapshot

    def fail(self, run_id: str, reason: str, now: datetime) -> DailyQuantRun:
        _require_utc(now)
        run = self._runs.get(run_id)
        if run is None:
            raise ValueError("unknown daily analysis run")
        failed = run.model_copy(update={"status": DailyQuantRunStatus.FAILED, "failure_reason": reason, "completed_at": now})
        self._runs[run_id] = failed
        return failed

    def run(self, run_id: str) -> DailyQuantRun | None:
        return self._runs.get(run_id)


def _snapshot_hash(snapshot: DailyAnalysisSnapshot) -> str:
    value = snapshot.model_dump(mode="json")
    value["canonical_content_hash"] = None
    return sha256(_canonical_json(value).encode()).hexdigest()


def _canonical_json(value: object) -> str:
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json")
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def _require_utc(value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
        raise ValueError("timestamp must use UTC")
