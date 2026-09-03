import os
from datetime import UTC, datetime
from pathlib import Path

import pytest

from src.research_automation.domain import ExperimentInput, ResearchExperiment
from src.research_automation.persistence import PostgresExperimentRepository

pytestmark = pytest.mark.skipif(
    "RESEARCH_AUTOMATION_DATABASE_URL" not in os.environ,
    reason="requires local PostgreSQL",
)


def _experiment(experiment_id: str) -> ResearchExperiment:
    input_value = ExperimentInput(
        hypothesis="验证持久化",
        data_version_id="dv-integration",
        data_artifact_uri="minio://artifacts/dv-integration.tar.gz",
        data_artifact_hash="e" * 64,
        script_id="fixed-factor-smoke-v1",
        parameters={"window": "20"},
        random_seed=11,
    )
    return ResearchExperiment.queue(experiment_id, input_value, datetime(2026, 9, 3, tzinfo=UTC))


def test_postgres_experiment_round_trip_and_idempotency() -> None:
    url = os.environ["RESEARCH_AUTOMATION_DATABASE_URL"]
    repository = PostgresExperimentRepository(url)
    repository.migrate(Path(__file__).parents[2] / "migrations/001_research_automation.sql")
    experiment = _experiment("integration-persistence-1")
    repository.save_submission(experiment, "integration-idempotency-1")
    repository.save_submission(experiment, "integration-idempotency-1")
    assert repository.get(experiment.experiment_id) == experiment
    assert repository.lookup_idempotency("integration-idempotency-1") == (
        experiment.experiment_id,
        experiment.input_hash,
    )
    with pytest.raises(ValueError, match="different input"):
        repository.save_submission(_experiment("integration-persistence-2"), "integration-idempotency-1")


def test_postgres_experiment_and_outbox_are_idempotent() -> None:
    url = os.environ["RESEARCH_AUTOMATION_DATABASE_URL"]
    repository = PostgresExperimentRepository(url)
    repository.migrate(Path(__file__).parents[2] / "migrations/001_research_automation.sql")
    experiment = _experiment("integration-persistence-outbox")
    repository.save_with_outbox(
        experiment,
        "integration-research-event-1",
        "stock.research.experiment.completed.v1",
        {"experimentId": experiment.experiment_id, "inputHash": experiment.input_hash},
    )
    repository.save_with_outbox(
        experiment,
        "integration-research-event-1",
        "stock.research.experiment.completed.v1",
        {"experimentId": experiment.experiment_id, "inputHash": experiment.input_hash},
    )
