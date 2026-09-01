from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from quant_research.baseline_model import BaselineModelError, train_linear_baseline
from quant_research.evaluation import (
    FactorReturnObservation,
    TemporalSplitDataset,
    TemporalSplitDefinition,
)
from quant_research.models import ModelAlgorithm, ModelDefinition, ModelVersion


def dataset() -> TemporalSplitDataset:
    rows = tuple(
        FactorReturnObservation(
            security_id=f"sh60000{index}",
            as_of_date=date(2026, 1, index + 1),
            feature_available_at=datetime(2026, 1, index + 1, 16, tzinfo=UTC),
            forward_return_start=date(2026, 1, index + 2),
            forward_return_end=date(2026, 1, index + 2),
            factor_value=Decimal(index),
            realized_return=Decimal(index * 2),
        )
        for index in (1, 2, 3)
    )
    split = TemporalSplitDefinition(
        train_start=date(2026, 1, 2), train_end=date(2026, 1, 2),
        validation_start=date(2026, 1, 3), validation_end=date(2026, 1, 3),
        test_start=date(2026, 1, 4), test_end=date(2026, 1, 4),
    )
    return TemporalSplitDataset(
        factor_id="price.momentum.2d", factor_version="v1", data_version_id="data-v1",
        split=split, train=rows, validation=rows, test=rows, canonical_content_hash="a" * 64,
    )


def model() -> tuple[ModelDefinition, ModelVersion]:
    return (
        ModelDefinition(
            model_id="linear-baseline", algorithm=ModelAlgorithm.LINEAR,
            feature_factor_ids=("price.momentum.2d",), target_name="forward_return",
        ),
        ModelVersion(
            model_id="linear-baseline", version="v1", code_hash="b" * 64,
            parameter_hash="c" * 64, data_version_id="data-v1", factor_set_version="factor-set-v1",
            temporal_split_hash="a" * 64, random_seed=7,
        ),
    )


def test_linear_baseline_is_deterministic_and_quantized() -> None:
    definition, version = model()
    result = train_linear_baseline(definition, version, dataset())
    repeat = train_linear_baseline(definition, version, dataset())
    assert result.intercept == Decimal("0E-8")
    assert result.coefficient == Decimal("2.00000000")
    assert result.canonical_content_hash == repeat.canonical_content_hash
    assert result.eligibility == "RESEARCH_ONLY"


def test_linear_baseline_rejects_non_linear_and_constant_features() -> None:
    definition, version = model()
    with pytest.raises(BaselineModelError, match="only supports"):
        train_linear_baseline(definition.model_copy(update={"algorithm": ModelAlgorithm.TREE}), version, dataset())
    constant = dataset().model_copy(
        update={"train": tuple(row.model_copy(update={"factor_value": Decimal(1)}) for row in dataset().train)}
    )
    with pytest.raises(BaselineModelError, match="constant"):
        train_linear_baseline(definition, version, constant)
