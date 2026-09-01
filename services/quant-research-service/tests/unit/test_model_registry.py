from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from quant_research.baseline_model import LinearBaselineModel, evaluate_linear_baseline
from quant_research.domain import ArtifactRef
from quant_research.evaluation import (
    FactorReturnObservation,
    TemporalSplitDataset,
    TemporalSplitDefinition,
)
from quant_research.metadata_repository import (
    InMemoryResearchMetadataRepository,
    MetadataConflictError,
)
from quant_research.models import (
    EvaluationMetric,
    EvaluationReport,
    ModelAlgorithm,
    ModelDefinition,
    ModelStatus,
    ModelVersion,
    TrainingRun,
    TrainingRunStatus,
)


def _split() -> TemporalSplitDataset:
    observation = FactorReturnObservation(
        security_id="sh600000",
        as_of_date=date(2026, 1, 2),
        feature_available_at=datetime(2026, 1, 2, 16, tzinfo=UTC),
        forward_return_start=date(2026, 1, 3),
        forward_return_end=date(2026, 1, 3),
        factor_value=Decimal(1),
        realized_return=Decimal("0.01"),
    )
    split = TemporalSplitDefinition(
        train_start=date(2026, 1, 2), train_end=date(2026, 1, 2),
        validation_start=date(2026, 1, 3), validation_end=date(2026, 1, 3),
        test_start=date(2026, 1, 4), test_end=date(2026, 1, 4),
    )
    return TemporalSplitDataset(
        factor_id="price.momentum.2d", factor_version="v1", data_version_id="data-v1",
        split=split, train=(observation,), validation=(observation,), test=(observation,),
        canonical_content_hash="a" * 64,
    )


def _model(split: TemporalSplitDataset) -> ModelVersion:
    return ModelVersion(
        model_id="baseline", version="v1", code_hash="b" * 64, parameter_hash="c" * 64,
        data_version_id="data-v1", factor_set_version="factor-set-v1",
        temporal_split_hash=split.canonical_content_hash, random_seed=7,
    )


def test_model_definition_and_training_run_keep_versions_bound() -> None:
    definition = ModelDefinition(
        model_id="baseline", algorithm=ModelAlgorithm.LINEAR,
        feature_factor_ids=("price.momentum.2d",), target_name="forward_return",
    )
    split = _split()
    run = TrainingRun(
        run_id="training-001", model=_model(split), split=split,
        started_at=datetime(2026, 1, 5, tzinfo=UTC),
    )
    assert definition.algorithm is ModelAlgorithm.LINEAR
    assert run.status is TrainingRunStatus.RUNNING
    with pytest.raises(ValueError, match="unique"):
        ModelDefinition(
            model_id="baseline", algorithm=ModelAlgorithm.LINEAR,
            feature_factor_ids=("price.momentum.2d", "price.momentum.2d"), target_name="return",
        )


def test_training_artifact_and_evaluation_status_gates() -> None:
    split = _split()
    model = _model(split)
    with pytest.raises(ValueError, match="require a model Artifact"):
        TrainingRun(
            run_id="training-002", model=model, split=split,
            started_at=datetime(2026, 1, 5, tzinfo=UTC), completed_at=datetime(2026, 1, 6, tzinfo=UTC),
            status=TrainingRunStatus.SUCCEEDED,
        )
    report = EvaluationReport(
        report_id="eval-001", model=model, training_run_id="training-001",
        metrics=(EvaluationMetric(name="ic", value=Decimal("0.1")),),
        evaluation_split="validation", prediction_count=1,
        out_of_sample=False, cost_model_version="cost-v1",
    )
    assert report.status is ModelStatus.CANDIDATE
    with pytest.raises(ValueError, match="in-sample"):
        EvaluationReport(
            report_id="eval-002", model=model, training_run_id="training-001",
            metrics=(EvaluationMetric(name="ic", value=Decimal("0.1")),),
            evaluation_split="validation", prediction_count=1,
            out_of_sample=False, cost_model_version="cost-v1", status=ModelStatus.ACTIVE,
        )
    artifact = ArtifactRef(uri="minio://artifacts/model", sha256="d" * 64)
    succeeded = TrainingRun(
        run_id="training-003", model=model, split=split,
        started_at=datetime(2026, 1, 5, tzinfo=UTC), completed_at=datetime(2026, 1, 6, tzinfo=UTC),
        status=TrainingRunStatus.SUCCEEDED, model_artifact=artifact,
    )
    assert succeeded.model_artifact == artifact


def test_baseline_evaluation_uses_only_out_of_sample_split() -> None:
    split = _split()
    model = _model(split)
    run = TrainingRun(
        run_id="training-eval", model=model, split=split,
        started_at=datetime(2026, 1, 5, tzinfo=UTC), completed_at=datetime(2026, 1, 6, tzinfo=UTC),
        status=TrainingRunStatus.SUCCEEDED,
        model_artifact=ArtifactRef(uri="minio://artifacts/model", sha256="d" * 64),
    )
    baseline = LinearBaselineModel(
        model_id="baseline", model_version="v1", data_version_id="data-v1",
        factor_id="price.momentum.2d", intercept=Decimal(0), coefficient=Decimal(1),
        training_row_count=2, canonical_content_hash="e" * 64,
    )
    report, predictions = evaluate_linear_baseline(
        baseline, run, split, split_name="test", cost_model_version="cost-v1"
    )
    assert report.out_of_sample is True
    assert report.evaluation_split == "test"
    assert report.prediction_count == len(predictions) == 1
    with pytest.raises(Exception, match="validation or test"):
        EvaluationReport(
            report_id="eval-train", model=model, training_run_id=run.run_id,
            evaluation_split="train", prediction_count=1,
            metrics=(EvaluationMetric(name="mae", value=Decimal(0)),),
            out_of_sample=False, cost_model_version="cost-v1",
        )


def test_metadata_repository_is_idempotent_and_rejects_rewrite() -> None:
    repository = InMemoryResearchMetadataRepository()
    split = _split()
    run = TrainingRun(
        run_id="metadata-run", model=_model(split), split=split,
        started_at=datetime(2026, 1, 5, tzinfo=UTC),
    )
    repository.save_training_run(run)
    repository.save_training_run(run)
    with pytest.raises(MetadataConflictError, match="different content"):
        repository.save_training_run(run.model_copy(update={"run_id": "metadata-run", "status": TrainingRunStatus.FAILED}))
