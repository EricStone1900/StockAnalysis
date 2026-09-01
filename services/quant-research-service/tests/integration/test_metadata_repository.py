import os
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest

from quant_research.backtest import BacktestExecutionInput, BacktestSide
from quant_research.cost_model import CostModelDefinition
from quant_research.evaluation import (
    FactorReturnObservation,
    TemporalSplitDataset,
    TemporalSplitDefinition,
)
from quant_research.metadata_repository import (
    MetadataConflictError,
    PostgresResearchMetadataRepository,
)
from quant_research.models import (
    EvaluationMetric,
    EvaluationReport,
    ModelVersion,
    TrainingRun,
    TrainingRunStatus,
)
from quant_research.portfolio_backtest import RoundTripTrade, run_portfolio_backtest

pytestmark = pytest.mark.skipif("MARKET_DATA_DATABASE_URL" not in os.environ, reason="requires local PostgreSQL")


def _split() -> TemporalSplitDataset:
    row = FactorReturnObservation(
        security_id="sh600000", as_of_date=date(2026, 1, 2),
        feature_available_at=datetime(2026, 1, 2, 16, tzinfo=UTC),
        forward_return_start=date(2026, 1, 3), forward_return_end=date(2026, 1, 3),
        factor_value=Decimal(1), realized_return=Decimal("0.01"),
    )
    window = TemporalSplitDefinition(
        train_start=date(2026, 1, 2), train_end=date(2026, 1, 2),
        validation_start=date(2026, 1, 3), validation_end=date(2026, 1, 3),
        test_start=date(2026, 1, 4), test_end=date(2026, 1, 4),
    )
    return TemporalSplitDataset(
        factor_id="price.momentum.2d", factor_version="v1", data_version_id="data-v1",
        split=window, train=(row,), validation=(row,), test=(row,), canonical_content_hash="a" * 64,
    )


def _model(split: TemporalSplitDataset) -> ModelVersion:
    return ModelVersion(
        model_id="baseline", version="v1", code_hash="b" * 64, parameter_hash="c" * 64,
        data_version_id=split.data_version_id, factor_set_version="factor-set-v1",
        temporal_split_hash=split.canonical_content_hash, random_seed=7,
    )


def _execution(side: BacktestSide, day: date, price: str) -> BacktestExecutionInput:
    return BacktestExecutionInput(
        security_id="sh600000", signal_date=date(2026, 1, 2), execution_date=day,
        side=side, requested_quantity=Decimal(100), execution_price=Decimal(price),
    )


def test_postgres_metadata_is_idempotent_and_recoverable() -> None:
    import psycopg

    repository = PostgresResearchMetadataRepository(os.environ["MARKET_DATA_DATABASE_URL"])
    repository.migrate(Path(__file__).parents[2] / "migrations/001_research_metadata.sql")
    suffix = uuid4().hex
    split = _split()
    run_id = f"integration-{suffix}"
    run = TrainingRun(
        run_id=run_id, model=_model(split), split=split,
        started_at=datetime(2026, 1, 5, tzinfo=UTC),
    )
    evaluation = EvaluationReport(
        report_id=f"evaluation-{suffix}", model=run.model, training_run_id=run_id,
        evaluation_split="validation", prediction_count=1,
        metrics=(EvaluationMetric(name="mae", value=Decimal("0.01")),),
        out_of_sample=True, cost_model_version="cost-v1",
    )
    backtest = run_portfolio_backtest(
        (RoundTripTrade(
            trade_id=f"trade-{suffix}",
            buy=_execution(BacktestSide.BUY, date(2026, 1, 3), "10"),
            sell=_execution(BacktestSide.SELL, date(2026, 1, 4), "11"),
        ),),
        CostModelDefinition(version="cost-v1", commission_rate=Decimal(0), stamp_tax_rate=Decimal(0), slippage_bps=Decimal(0), minimum_commission=Decimal(0)),
    )
    try:
        repository.save_training_run(run)
        repository.save_training_run(run)
        repository.save_evaluation_report(evaluation)
        repository.save_backtest_report(f"backtest-{suffix}", backtest)
        assert repository.get_training_run(run_id) == run
        assert repository.get_evaluation_report(evaluation.report_id) == evaluation
        assert repository.get_backtest_report(f"backtest-{suffix}") == backtest
        with pytest.raises(MetadataConflictError):
            repository.save_training_run(run.model_copy(update={"status": TrainingRunStatus.FAILED}))
    finally:
        with psycopg.connect(os.environ["MARKET_DATA_DATABASE_URL"]) as connection:
            connection.execute(
                "DELETE FROM research_metadata_records WHERE record_id LIKE %s",
                (f"%{suffix}",),
            )
