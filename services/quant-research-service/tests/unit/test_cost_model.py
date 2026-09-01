from decimal import Decimal

import pytest

from quant_research.cost_model import (
    CostEvaluationObservation,
    CostModelDefinition,
    estimate_trade_cost,
    evaluate_cost_adjusted_returns,
)
from quant_research.models import EvaluationMetric, EvaluationReport, ModelVersion


def model() -> ModelVersion:
    return ModelVersion(
        model_id="baseline", version="v1", code_hash="a" * 64, parameter_hash="b" * 64,
        data_version_id="data-v1", factor_set_version="factor-set-v1", temporal_split_hash="c" * 64,
        random_seed=7,
    )


def report() -> EvaluationReport:
    return EvaluationReport(
        report_id="eval-test", model=model(), training_run_id="run-001",
        evaluation_split="test", prediction_count=2,
        metrics=(EvaluationMetric(name="mae", value=Decimal("0.01000000")),),
        out_of_sample=True, cost_model_version="none-v1",
    )


def test_trade_cost_applies_minimum_commission_and_sell_stamp_tax() -> None:
    definition = CostModelDefinition(
        version="cn-a-v1", commission_rate=Decimal("0.0003"), stamp_tax_rate=Decimal("0.001"),
        slippage_bps=Decimal(2), minimum_commission=Decimal(5),
    )
    result = estimate_trade_cost(definition, buy_notional=Decimal(10000), sell_notional=Decimal(20000))
    assert result.commission == Decimal("11.00000000")
    assert result.stamp_tax == Decimal("20.00000000")
    assert result.slippage == Decimal("6.00000000")
    assert result.total_cost == Decimal("37.00000000")


def test_cost_adjusted_report_is_separate_and_reproducible() -> None:
    definition = CostModelDefinition(
        version="cn-a-v1", commission_rate=Decimal("0.0003"), stamp_tax_rate=Decimal("0.001"),
        slippage_bps=Decimal(0), minimum_commission=Decimal(0),
    )
    observations = (
        CostEvaluationObservation(gross_return=Decimal("0.10"), buy_notional=Decimal(100), sell_notional=Decimal(0)),
        CostEvaluationObservation(gross_return=Decimal("0.20"), buy_notional=Decimal(0), sell_notional=Decimal(100)),
    )
    result = evaluate_cost_adjusted_returns(report(), definition, observations)
    repeat = evaluate_cost_adjusted_returns(report(), definition, observations)
    assert result.mean_gross_return == Decimal("0.15000000")
    assert result.mean_transaction_cost == Decimal("0.08000000")
    assert result.mean_net_return == Decimal("0.07000000")
    assert result.canonical_content_hash == repeat.canonical_content_hash
    with pytest.raises(ValueError, match="match"):
        evaluate_cost_adjusted_returns(report().model_copy(update={"prediction_count": 1}), definition, observations)
