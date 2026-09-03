"""研究实验 PostgreSQL 仓储；大对象只保存 URI 和 Hash。"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from .application import ResearchOutboxEvent
from .domain import (
    ExperimentInput,
    ExperimentRun,
    ExperimentStatus,
    ResearchExperiment,
    SandboxBudget,
)


class PostgresExperimentRepository:
    def __init__(self, database_url: str) -> None:
        self._database_url = database_url

    def migrate(self, migration: Path) -> None:
        import psycopg

        with psycopg.connect(self._database_url, autocommit=True) as connection:
            connection.execute(migration.read_text(encoding="utf-8"))

    def get(self, experiment_id: str) -> ResearchExperiment | None:
        import psycopg

        with psycopg.connect(self._database_url) as connection:
            row = connection.execute(
                "SELECT payload::text FROM research_experiments WHERE experiment_id=%s",
                (experiment_id,),
            ).fetchone()
        return None if row is None else _from_payload(json.loads(str(row[0])))

    def lookup_idempotency(self, key: str) -> tuple[str, str] | None:
        import psycopg

        with psycopg.connect(self._database_url) as connection:
            row = connection.execute(
                "SELECT experiment_id, input_hash FROM research_experiment_idempotency WHERE idempotency_key=%s",
                (key,),
            ).fetchone()
        return None if row is None else (str(row[0]), str(row[1]))

    def save_submission(self, experiment: ResearchExperiment, idempotency_key: str) -> None:
        import psycopg

        payload = _canonical(_to_payload(experiment))
        with psycopg.connect(self._database_url) as connection:
            idem = connection.execute(
                "SELECT experiment_id, input_hash FROM research_experiment_idempotency WHERE idempotency_key=%s FOR UPDATE",
                (idempotency_key,),
            ).fetchone()
            if idem is not None and (str(idem[0]) != experiment.experiment_id or str(idem[1]) != experiment.input_hash):
                raise ValueError("idempotency key is already bound to different input")
            existing = connection.execute(
                "SELECT payload::text FROM research_experiments WHERE experiment_id=%s FOR UPDATE",
                (experiment.experiment_id,),
            ).fetchone()
            if existing is not None:
                if _canonical(json.loads(str(existing[0]))) != payload:
                    raise ValueError("experiment already contains different content")
                return
            connection.execute(
                "INSERT INTO research_experiments(experiment_id,input_hash,payload,created_at) VALUES (%s,%s,%s::jsonb,%s)",
                (experiment.experiment_id, experiment.input_hash, payload, experiment.created_at),
            )
            if idem is None:
                connection.execute(
                    "INSERT INTO research_experiment_idempotency(idempotency_key,experiment_id,input_hash) VALUES (%s,%s,%s)",
                    (idempotency_key, experiment.experiment_id, experiment.input_hash),
                )

    def save(self, experiment: ResearchExperiment) -> None:
        import psycopg

        payload = _canonical(_to_payload(experiment))
        with psycopg.connect(self._database_url) as connection:
            existing = connection.execute(
                "SELECT payload::text FROM research_experiments WHERE experiment_id=%s FOR UPDATE",
                (experiment.experiment_id,),
            ).fetchone()
            if existing is not None and _canonical(json.loads(str(existing[0]))) == payload:
                return
            if existing is not None:
                connection.execute(
                    "UPDATE research_experiments SET input_hash=%s,payload=%s::jsonb WHERE experiment_id=%s",
                    (experiment.input_hash, payload, experiment.experiment_id),
                )
            else:
                connection.execute(
                    "INSERT INTO research_experiments(experiment_id,input_hash,payload,created_at) VALUES (%s,%s,%s::jsonb,%s)",
                    (experiment.experiment_id, experiment.input_hash, payload, experiment.created_at),
                )

    def save_with_outbox(self, experiment: ResearchExperiment, event: ResearchOutboxEvent) -> None:
        import psycopg

        payload = _canonical(_to_payload(experiment))
        event_payload = _canonical(event.payload)
        with psycopg.connect(self._database_url) as connection:
            connection.execute(
                "INSERT INTO research_experiments(experiment_id,input_hash,payload,created_at) VALUES (%s,%s,%s::jsonb,%s) ON CONFLICT (experiment_id) DO UPDATE SET input_hash=EXCLUDED.input_hash,payload=EXCLUDED.payload",
                (experiment.experiment_id, experiment.input_hash, payload, experiment.created_at),
            )
            row = connection.execute("SELECT subject,payload::text FROM research_experiment_outbox WHERE event_id=%s", (event.event_id,)).fetchone()
            if row is not None and (str(row[0]) != event.subject or _canonical(json.loads(str(row[1]))) != event_payload):
                raise ValueError("outbox event id already contains different content")
            if row is None:
                connection.execute(
                    "INSERT INTO research_experiment_outbox(event_id,experiment_id,subject,payload) VALUES (%s,%s,%s,%s::jsonb)",
                    (event.event_id, experiment.experiment_id, event.subject, event_payload),
                )

    def pending_outbox(self, limit: int = 100) -> tuple[ResearchOutboxEvent, ...]:
        if limit < 1:
            raise ValueError("limit must be positive")
        import psycopg

        with psycopg.connect(self._database_url) as connection:
            rows = connection.execute(
                "SELECT event_id,experiment_id,subject,payload::text FROM research_experiment_outbox WHERE published_at IS NULL ORDER BY created_at,event_id LIMIT %s",
                (limit,),
            ).fetchall()
        return tuple(ResearchOutboxEvent(str(row[0]), str(row[1]), str(row[2]), json.loads(str(row[3]))) for row in rows)

    def mark_outbox_published(self, event_id: str, published_at: datetime) -> None:
        import psycopg

        with psycopg.connect(self._database_url) as connection:
            connection.execute(
                "UPDATE research_experiment_outbox SET published_at=%s WHERE event_id=%s AND published_at IS NULL",
                (published_at, event_id),
            )


def _to_payload(experiment: ResearchExperiment) -> dict[str, Any]:
    value = experiment.input
    run = experiment.run
    return {
        "experimentId": experiment.experiment_id,
        "status": experiment.status.value,
        "createdAt": experiment.created_at.isoformat(),
        "inputHash": experiment.input_hash,
        "input": {
            "hypothesis": value.hypothesis, "dataVersionId": value.data_version_id,
            "dataArtifactUri": value.data_artifact_uri, "dataArtifactHash": value.data_artifact_hash,
            "scriptId": value.script_id, "parameters": dict(value.parameters), "randomSeed": value.random_seed,
            "budget": value.budget.__dict__,
        },
        "run": None if run is None else {
            "runId": run.run_id, "status": run.status.value, "sandboxConfigHash": run.sandbox_config_hash,
            "startedAt": None if run.started_at is None else run.started_at.isoformat(),
            "completedAt": None if run.completed_at is None else run.completed_at.isoformat(),
            "exitCode": run.exit_code, "metrics": run.metrics, "rejectionReason": run.rejection_reason,
        },
    }


def _from_payload(payload: dict[str, Any]) -> ResearchExperiment:
    value = payload["input"]
    input_value = ExperimentInput(
        hypothesis=value["hypothesis"], data_version_id=value["dataVersionId"], data_artifact_uri=value["dataArtifactUri"],
        data_artifact_hash=value["dataArtifactHash"], script_id=value["scriptId"], parameters=value["parameters"],
        random_seed=value["randomSeed"], budget=SandboxBudget(**value["budget"]),
    )
    raw_run = payload.get("run")
    run = None if raw_run is None else ExperimentRun(
        run_id=raw_run["runId"], status=ExperimentStatus(raw_run["status"]), sandbox_config_hash=raw_run["sandboxConfigHash"],
        started_at=_parse_time(raw_run.get("startedAt")), completed_at=_parse_time(raw_run.get("completedAt")),
        exit_code=raw_run.get("exitCode"), metrics=raw_run.get("metrics"), rejection_reason=raw_run.get("rejectionReason"),
    )
    return ResearchExperiment(
        experiment_id=payload["experimentId"], input=input_value, status=ExperimentStatus(payload["status"]),
        created_at=_parse_required_time(payload["createdAt"]), input_hash=payload["inputHash"], run=run,
    )


def _parse_time(value: str | None) -> datetime | None:
    return None if value is None else datetime.fromisoformat(value)


def _parse_required_time(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _canonical(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
