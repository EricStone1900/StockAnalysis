"""阶段04-01实验领域模型；不依赖Docker、RD-Agent或生产服务。"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from enum import StrEnum
from hashlib import sha256


class ExperimentStatus(StrEnum):
    DRAFT = "DRAFT"
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    EVALUATED = "EVALUATED"
    REJECTED = "REJECTED"
    PROMOTION_REQUESTED = "PROMOTION_REQUESTED"


@dataclass(frozen=True)
class SandboxBudget:
    cpu_limit: float
    memory_mb: int
    disk_mb: int
    pid_limit: int
    timeout_seconds: int
    log_limit_bytes: int

    def __post_init__(self) -> None:
        if self.cpu_limit <= 0 or self.memory_mb <= 0 or self.disk_mb <= 0:
            raise ValueError("sandbox resource limits must be positive")
        if self.pid_limit < 1 or self.timeout_seconds < 1 or self.log_limit_bytes < 1:
            raise ValueError("sandbox execution limits must be positive")


DEFAULT_SANDBOX_BUDGET = SandboxBudget(
    cpu_limit=1.0,
    memory_mb=512,
    disk_mb=256,
    pid_limit=64,
    timeout_seconds=60,
    log_limit_bytes=65536,
)


@dataclass(frozen=True)
class ExperimentInput:
    hypothesis: str
    data_version_id: str
    data_artifact_uri: str
    data_artifact_hash: str
    script_id: str
    parameters: Mapping[str, str]
    random_seed: int
    budget: SandboxBudget = DEFAULT_SANDBOX_BUDGET

    def __post_init__(self) -> None:
        if not self.hypothesis.strip() or not self.data_version_id.strip() or not self.script_id.strip():
            raise ValueError("hypothesis, data_version_id and script_id are required")
        if not self.data_artifact_uri.startswith(("s3://", "minio://")):
            raise ValueError("data artifact must be an immutable object-store URI")
        if len(self.data_artifact_hash) != 64:
            raise ValueError("data artifact hash must be SHA-256")

    @property
    def content_hash(self) -> str:
        payload = {
            "hypothesis": self.hypothesis,
            "dataVersionId": self.data_version_id,
            "dataArtifactUri": self.data_artifact_uri,
            "dataArtifactHash": self.data_artifact_hash,
            "scriptId": self.script_id,
            "parameters": dict(sorted(self.parameters.items())),
            "randomSeed": self.random_seed,
            "budget": self.budget.__dict__,
        }
        return sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


@dataclass(frozen=True)
class ExperimentRun:
    run_id: str
    status: ExperimentStatus
    sandbox_config_hash: str
    started_at: datetime | None = None
    completed_at: datetime | None = None
    exit_code: int | None = None
    metrics: Mapping[str, float] | None = None
    rejection_reason: str | None = None


@dataclass(frozen=True)
class ResearchExperiment:
    experiment_id: str
    input: ExperimentInput
    status: ExperimentStatus
    created_at: datetime
    input_hash: str
    run: ExperimentRun | None = None

    @classmethod
    def queue(cls, experiment_id: str, input_value: ExperimentInput, now: datetime) -> ResearchExperiment:
        _require_utc(now)
        if not experiment_id.strip():
            raise ValueError("experiment_id is required")
        return cls(experiment_id, input_value, ExperimentStatus.QUEUED, now, input_value.content_hash)

    def start(self, run_id: str, sandbox_config_hash: str, now: datetime) -> ResearchExperiment:
        _require_utc(now)
        if self.status is not ExperimentStatus.QUEUED:
            raise ValueError("only queued experiments can start")
        return replace(
            self,
            status=ExperimentStatus.RUNNING,
            run=ExperimentRun(run_id, ExperimentStatus.RUNNING, sandbox_config_hash, started_at=now),
        )

    def evaluate(self, metrics: Mapping[str, float], exit_code: int, now: datetime) -> ResearchExperiment:
        _require_utc(now)
        if self.status is not ExperimentStatus.RUNNING or self.run is None:
            raise ValueError("only running experiments can be evaluated")
        if exit_code != 0:
            return self.reject(f"sandbox exited with code {exit_code}", exit_code, now)
        return replace(
            self,
            status=ExperimentStatus.EVALUATED,
            run=replace(self.run, status=ExperimentStatus.EVALUATED, completed_at=now, exit_code=0, metrics=dict(metrics)),
        )

    def reject(self, reason: str, exit_code: int | None, now: datetime) -> ResearchExperiment:
        _require_utc(now)
        if self.status not in {ExperimentStatus.QUEUED, ExperimentStatus.RUNNING}:
            raise ValueError("only queued or running experiments can be rejected")
        run = self.run or ExperimentRun(f"{self.experiment_id}:rejected", ExperimentStatus.REJECTED, "", started_at=None)
        return replace(
            self,
            status=ExperimentStatus.REJECTED,
            run=replace(run, status=ExperimentStatus.REJECTED, completed_at=now, exit_code=exit_code, rejection_reason=reason),
        )


def utc_now() -> datetime:
    return datetime.now(UTC)


def _require_utc(value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
        raise ValueError("timestamps must be UTC")
