"""实验应用服务与内存仓储。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol
from uuid import uuid4

from .domain import ExperimentInput, ResearchExperiment, utc_now
from .sandbox import FixedScriptSandbox, SandboxCommand, SandboxExecution, SandboxExecutor


@dataclass(frozen=True)
class SubmittedExperiment:
    experiment: ResearchExperiment
    created: bool


@dataclass(frozen=True)
class ResearchOutboxEvent:
    event_id: str
    experiment_id: str
    subject: str
    payload: dict[str, Any]


class ExperimentRepository(Protocol):
    def lookup_idempotency(self, key: str) -> tuple[str, str] | None: ...
    def save_submission(self, experiment: ResearchExperiment, idempotency_key: str) -> None: ...
    def save(self, experiment: ResearchExperiment) -> None: ...
    def get(self, experiment_id: str) -> ResearchExperiment | None: ...
    def save_with_outbox(self, experiment: ResearchExperiment, event: ResearchOutboxEvent) -> None: ...
    def pending_outbox(self, limit: int = 100) -> tuple[ResearchOutboxEvent, ...]: ...


class InMemoryExperimentRepository:
    def __init__(self) -> None:
        self.experiments: dict[str, ResearchExperiment] = {}
        self.idempotency: dict[str, tuple[str, str]] = {}
        self.outbox: dict[str, ResearchOutboxEvent] = {}

    def lookup_idempotency(self, key: str) -> tuple[str, str] | None:
        return self.idempotency.get(key)

    def save_submission(self, experiment: ResearchExperiment, idempotency_key: str) -> None:
        self.experiments[experiment.experiment_id] = experiment
        self.idempotency[idempotency_key] = (experiment.experiment_id, experiment.input_hash)

    def save(self, experiment: ResearchExperiment) -> None:
        self.experiments[experiment.experiment_id] = experiment

    def get(self, experiment_id: str) -> ResearchExperiment | None:
        return self.experiments.get(experiment_id)

    def save_with_outbox(self, experiment: ResearchExperiment, event: ResearchOutboxEvent) -> None:
        self.save(experiment)
        existing = self.outbox.get(event.event_id)
        if existing is not None and existing != event:
            raise ValueError("outbox event id already contains different content")
        self.outbox[event.event_id] = event

    def pending_outbox(self, limit: int = 100) -> tuple[ResearchOutboxEvent, ...]:
        if limit < 1:
            raise ValueError("limit must be positive")
        return tuple(self.outbox.values())[:limit]


class ExperimentService:
    def __init__(self, repository: ExperimentRepository, sandbox: FixedScriptSandbox) -> None:
        self._repository = repository
        self._sandbox = sandbox

    def submit(self, experiment_id: str, idempotency_key: str, input_value: ExperimentInput, now: datetime | None = None) -> SubmittedExperiment:
        if not idempotency_key.strip():
            raise ValueError("Idempotency-Key is required")
        existing = self._repository.lookup_idempotency(idempotency_key)
        if existing is not None:
            existing_id, existing_hash = existing
            if existing_id != experiment_id or existing_hash != input_value.content_hash:
                raise ValueError("idempotency key is already bound to different input")
            existing_experiment = self._repository.get(experiment_id)
            if existing_experiment is None:
                raise ValueError("idempotency record has no experiment")
            return SubmittedExperiment(existing_experiment, False)
        if self._repository.get(experiment_id) is not None:
            raise ValueError("experiment_id already exists")
        self._sandbox.build_command(input_value)
        experiment = ResearchExperiment.queue(experiment_id, input_value, now or utc_now())
        self._repository.save_submission(experiment, idempotency_key)
        return SubmittedExperiment(experiment, True)

    def get(self, experiment_id: str) -> ResearchExperiment | None:
        return self._repository.get(experiment_id)

    def start(self, experiment_id: str, now: datetime | None = None) -> tuple[ResearchExperiment, SandboxCommand]:
        experiment = self._require(experiment_id)
        command = self._sandbox.build_command(experiment.input)
        updated = experiment.start(str(uuid4()), command.config_hash, now or utc_now())
        self._repository.save(updated)
        return updated, command

    def run_once(
        self,
        experiment_id: str,
        executor: SandboxExecutor,
        now: datetime | None = None,
    ) -> ResearchExperiment:
        started, _ = self.start(experiment_id, now)
        execution: SandboxExecution = self._sandbox.execute(started.input, executor)
        completed_at = now or utc_now()
        if execution.rejected_reason is not None:
            updated = started.reject(execution.rejected_reason, execution.exit_code, completed_at)
        else:
            updated = started.evaluate(execution.metrics, execution.exit_code or 0, completed_at)
        event = ResearchOutboxEvent(
            event_id=f"research-experiment-completed-{updated.experiment_id}-{updated.input_hash[:12]}",
            experiment_id=updated.experiment_id,
            subject="stock.research.experiment.completed.v1",
            payload={"experimentId": updated.experiment_id, "inputHash": updated.input_hash, "status": updated.status.value},
        )
        self._repository.save_with_outbox(updated, event)
        return updated

    def pending_outbox(self, limit: int = 100) -> tuple[ResearchOutboxEvent, ...]:
        return self._repository.pending_outbox(limit)

    def _require(self, experiment_id: str) -> ResearchExperiment:
        experiment = self.get(experiment_id)
        if experiment is None:
            raise KeyError(experiment_id)
        return experiment
