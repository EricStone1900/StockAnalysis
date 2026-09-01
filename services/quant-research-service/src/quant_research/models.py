"""模型注册与训练运行领域契约；真实训练由后续 Worker 实现。"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from quant_research.domain import ArtifactRef
from quant_research.evaluation import TemporalSplitDataset


class ModelAlgorithm(StrEnum):
    LINEAR = "LINEAR"
    TREE = "TREE"
    QLIB = "QLIB"


class ModelStatus(StrEnum):
    DRAFT = "DRAFT"
    CANDIDATE = "CANDIDATE"
    ACTIVE = "ACTIVE"
    RETIRED = "RETIRED"


class ModelDefinition(BaseModel):
    model_config = ConfigDict(frozen=True)

    model_id: str = Field(min_length=1)
    algorithm: ModelAlgorithm
    feature_factor_ids: tuple[str, ...] = Field(min_length=1)
    target_name: str = Field(min_length=1)
    frequency: str = "DAILY"

    @model_validator(mode="after")
    def require_unique_features(self) -> ModelDefinition:
        if len(set(self.feature_factor_ids)) != len(self.feature_factor_ids):
            raise ValueError("model feature_factor_ids must be unique")
        return self


class ModelVersion(BaseModel):
    model_config = ConfigDict(frozen=True)

    model_id: str = Field(min_length=1)
    version: str = Field(min_length=1)
    code_hash: str = Field(min_length=64, max_length=64)
    parameter_hash: str = Field(min_length=64, max_length=64)
    data_version_id: str = Field(min_length=1)
    factor_set_version: str = Field(min_length=1)
    temporal_split_hash: str = Field(min_length=64, max_length=64)
    random_seed: int = Field(ge=0)
    status: ModelStatus = ModelStatus.DRAFT

    @field_validator("code_hash", "parameter_hash", "temporal_split_hash")
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if any(character not in "0123456789abcdef" for character in value):
            raise ValueError("model hashes must be lowercase hexadecimal SHA-256 digests")
        return value


class TrainingRunStatus(StrEnum):
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


class TrainingRun(BaseModel):
    model_config = ConfigDict(frozen=True)

    run_id: str = Field(min_length=1)
    model: ModelVersion
    split: TemporalSplitDataset
    started_at: datetime
    completed_at: datetime | None = None
    status: TrainingRunStatus = TrainingRunStatus.RUNNING
    model_artifact: ArtifactRef | None = None

    @field_validator("started_at", "completed_at")
    @classmethod
    def require_utc_timestamp(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value)):
            raise ValueError("training timestamps must use UTC")
        return value

    @model_validator(mode="after")
    def validate_run_binding(self) -> TrainingRun:
        if self.split.data_version_id != self.model.data_version_id:
            raise ValueError("training split and model DataVersion do not match")
        if self.split.canonical_content_hash != self.model.temporal_split_hash:
            raise ValueError("training split does not match the model temporal split hash")
        if self.status is TrainingRunStatus.SUCCEEDED and self.model_artifact is None:
            raise ValueError("successful training runs require a model Artifact")
        if self.status is TrainingRunStatus.FAILED and self.model_artifact is not None:
            raise ValueError("failed training runs cannot publish a model Artifact")
        if self.completed_at is not None and self.completed_at < self.started_at:
            raise ValueError("training completed_at must not precede started_at")
        return self


class EvaluationMetric(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str = Field(min_length=1)
    value: Decimal


class EvaluationReport(BaseModel):
    """模型评估报告；不满足样本外与成本门禁时不得进入 ACTIVE。"""

    model_config = ConfigDict(frozen=True)

    report_id: str = Field(min_length=1)
    model: ModelVersion
    training_run_id: str = Field(min_length=1)
    evaluation_split: str = Field(min_length=1)
    prediction_count: int = Field(ge=1)
    metrics: tuple[EvaluationMetric, ...] = Field(min_length=1)
    out_of_sample: bool
    cost_model_version: str = Field(min_length=1)
    status: ModelStatus = ModelStatus.CANDIDATE

    @model_validator(mode="after")
    def enforce_candidate_gate(self) -> EvaluationReport:
        if self.evaluation_split not in {"validation", "test"}:
            raise ValueError("evaluation reports must use validation or test data")
        names = [metric.name for metric in self.metrics]
        if len(set(names)) != len(names):
            raise ValueError("evaluation metric names must be unique")
        if self.status is ModelStatus.ACTIVE and not self.out_of_sample:
            raise ValueError("an in-sample evaluation cannot activate a model")
        return self
