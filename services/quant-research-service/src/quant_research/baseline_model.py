"""首版线性基线模型；仅使用已冻结时序切分的训练集。"""

from __future__ import annotations

import json
from decimal import ROUND_HALF_EVEN, Decimal
from hashlib import sha256

from pydantic import BaseModel, ConfigDict, Field

from quant_research.evaluation import TemporalSplitDataset
from quant_research.models import (
    EvaluationMetric,
    EvaluationReport,
    ModelAlgorithm,
    ModelDefinition,
    ModelVersion,
    TrainingRun,
    TrainingRunStatus,
)

_PRECISION = Decimal("0.00000001")


class BaselineModelError(ValueError):
    """基线模型输入或计算不满足确定性要求。"""


class LinearBaselineModel(BaseModel):
    """可审计的单因子线性模型参数；尚未写入模型 Artifact。"""

    model_config = ConfigDict(frozen=True)

    model_id: str
    model_version: str
    data_version_id: str
    factor_id: str
    intercept: Decimal
    coefficient: Decimal
    training_row_count: int = Field(ge=2)
    canonical_content_hash: str = Field(min_length=64, max_length=64)
    eligibility: str = "RESEARCH_ONLY"


class BaselinePrediction(BaseModel):
    model_config = ConfigDict(frozen=True)

    security_id: str
    as_of_date: str
    actual: Decimal
    predicted: Decimal


def evaluate_linear_baseline(
    baseline: LinearBaselineModel,
    training_run: TrainingRun,
    dataset: TemporalSplitDataset,
    *,
    split_name: str,
    cost_model_version: str,
) -> tuple[EvaluationReport, tuple[BaselinePrediction, ...]]:
    """只在validation/test上评估已成功训练的基线模型。"""
    if training_run.status is not TrainingRunStatus.SUCCEEDED:
        raise BaselineModelError("evaluation requires a succeeded training run")
    if training_run.model.model_id != baseline.model_id or training_run.model.version != baseline.model_version:
        raise BaselineModelError("baseline parameters and training run model do not match")
    if dataset.data_version_id != baseline.data_version_id:
        raise BaselineModelError("baseline and evaluation dataset DataVersions do not match")
    if split_name == "validation":
        rows = dataset.validation
    elif split_name == "test":
        rows = dataset.test
    else:
        raise BaselineModelError("baseline evaluation split must be validation or test")
    predictions = tuple(
        BaselinePrediction(
            security_id=row.security_id,
            as_of_date=row.as_of_date.isoformat(),
            actual=row.realized_return,
            predicted=_quantize(baseline.intercept + baseline.coefficient * row.factor_value),
        )
        for row in rows
    )
    if not predictions:
        raise BaselineModelError("baseline evaluation requires evaluation rows")
    errors = [prediction.predicted - prediction.actual for prediction in predictions]
    mean_actual = sum((prediction.actual for prediction in predictions), Decimal(0)) / Decimal(len(predictions))
    total_sum = sum(((prediction.actual - mean_actual) ** 2 for prediction in predictions), Decimal(0))
    residual_sum = sum((error**2 for error in errors), Decimal(0))
    metrics = (
        EvaluationMetric(name="mae", value=_quantize(sum((abs(error) for error in errors), Decimal(0)) / Decimal(len(errors)))),
        EvaluationMetric(name="mse", value=_quantize(residual_sum / Decimal(len(errors)))),
        EvaluationMetric(name="r2", value=_quantize(Decimal(1) - residual_sum / total_sum) if total_sum else Decimal(0)),
    )
    return (
        EvaluationReport(
            report_id=f"{training_run.run_id}-{split_name}",
            model=training_run.model,
            training_run_id=training_run.run_id,
            evaluation_split=split_name,
            prediction_count=len(predictions),
            metrics=metrics,
            out_of_sample=True,
            cost_model_version=cost_model_version,
        ),
        predictions,
    )


def train_linear_baseline(
    definition: ModelDefinition,
    version: ModelVersion,
    dataset: TemporalSplitDataset,
) -> LinearBaselineModel:
    """用训练集闭式解拟合 y = intercept + coefficient * factor。"""
    if definition.algorithm is not ModelAlgorithm.LINEAR:
        raise BaselineModelError("baseline trainer only supports LINEAR models")
    if version.model_id != definition.model_id:
        raise BaselineModelError("model definition and version do not match")
    if len(definition.feature_factor_ids) != 1 or definition.feature_factor_ids[0] != dataset.factor_id:
        raise BaselineModelError("baseline trainer requires exactly the split factor as its sole feature")
    if version.data_version_id != dataset.data_version_id:
        raise BaselineModelError("model and training dataset DataVersions do not match")
    rows = dataset.train
    if len(rows) < 2:
        raise BaselineModelError("linear baseline requires at least two training rows")
    mean_x = sum((row.factor_value for row in rows), Decimal(0)) / Decimal(len(rows))
    mean_y = sum((row.realized_return for row in rows), Decimal(0)) / Decimal(len(rows))
    variance = sum(((row.factor_value - mean_x) ** 2 for row in rows), Decimal(0))
    if variance == 0:
        raise BaselineModelError("linear baseline cannot fit a constant feature")
    covariance = sum(
        ((row.factor_value - mean_x) * (row.realized_return - mean_y) for row in rows), Decimal(0)
    )
    coefficient = _quantize(covariance / variance)
    intercept = _quantize(mean_y - coefficient * mean_x)
    payload = {
        "modelId": definition.model_id,
        "modelVersion": version.version,
        "dataVersionId": dataset.data_version_id,
        "factorId": dataset.factor_id,
        "intercept": format(intercept, "f"),
        "coefficient": format(coefficient, "f"),
        "trainingRowCount": len(rows),
        "temporalSplitHash": dataset.canonical_content_hash,
    }
    canonical = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return LinearBaselineModel(
        model_id=definition.model_id,
        model_version=version.version,
        data_version_id=dataset.data_version_id,
        factor_id=dataset.factor_id,
        intercept=intercept,
        coefficient=coefficient,
        training_row_count=len(rows),
        canonical_content_hash=sha256(canonical.encode("utf-8")).hexdigest(),
    )


def _quantize(value: Decimal) -> Decimal:
    return value.quantize(_PRECISION, rounding=ROUND_HALF_EVEN)
