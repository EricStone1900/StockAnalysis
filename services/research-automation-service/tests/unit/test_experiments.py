from datetime import UTC, datetime

import pytest

from src.research_automation.application import ExperimentService, InMemoryExperimentRepository
from src.research_automation.domain import ExperimentInput, ExperimentStatus
from src.research_automation.sandbox import FixedScriptSandbox, SandboxExecution


def _input(script_id: str = "fixed-factor-smoke-v1") -> ExperimentInput:
    return ExperimentInput(
        hypothesis="验证固定价格因子脚本",
        data_version_id="data-version-v1",
        data_artifact_uri="minio://market-data/data-version-v1.tar.gz",
        data_artifact_hash="a" * 64,
        script_id=script_id,
        parameters={"window": "20"},
        random_seed=7,
    )


def test_submit_is_idempotent_and_rejects_rebound_key() -> None:
    service = ExperimentService(InMemoryExperimentRepository(), FixedScriptSandbox())
    submitted = service.submit("experiment-1", "key-1", _input())
    repeated = service.submit("experiment-1", "key-1", _input())
    assert submitted.created is True
    assert repeated.created is False
    with pytest.raises(ValueError, match="different input"):
        service.submit("experiment-2", "key-1", _input())


def test_started_experiment_uses_stable_sandbox_config() -> None:
    service = ExperimentService(InMemoryExperimentRepository(), FixedScriptSandbox())
    service.submit("experiment-1", "key-1", _input())
    started, command = service.start("experiment-1", datetime(2026, 9, 3, tzinfo=UTC))
    assert started.status is ExperimentStatus.RUNNING
    assert started.run is not None
    assert started.run.sandbox_config_hash == command.config_hash


def test_non_allow_list_script_is_rejected_before_queueing() -> None:
    service = ExperimentService(InMemoryExperimentRepository(), FixedScriptSandbox())
    with pytest.raises(ValueError, match="allow-listed"):
        service.submit("experiment-1", "key-1", _input("python -c 'import os'"))
    assert service.get("experiment-1") is None


def test_failed_sandbox_rejects_only_its_own_experiment() -> None:
    service = ExperimentService(InMemoryExperimentRepository(), FixedScriptSandbox())
    service.submit("experiment-fails", "key-fails", _input())
    service.submit("experiment-other", "key-other", _input())
    failed = service.run_once(
        "experiment-fails",
        lambda _command, _timeout, _limit: SandboxExecution(None, {}, "sandbox timeout"),
        datetime(2026, 9, 3, tzinfo=UTC),
    )
    assert failed.status is ExperimentStatus.REJECTED
    other = service.get("experiment-other")
    assert other is not None
    assert other.status is ExperimentStatus.QUEUED
