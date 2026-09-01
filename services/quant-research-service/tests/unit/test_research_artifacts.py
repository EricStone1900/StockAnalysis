from datetime import date
from decimal import Decimal
from hashlib import sha256

from quant_research.backtest import BacktestExecutionInput, BacktestSide
from quant_research.baseline_model import LinearBaselineModel
from quant_research.cost_model import CostModelDefinition
from quant_research.portfolio_backtest import RoundTripTrade, run_portfolio_backtest
from quant_research.research_artifacts import ResearchArtifactPublisher


class Writer:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    def put_immutable(self, key: str, content: bytes) -> str:
        if key in self.objects and self.objects[key] != content:
            raise ValueError("immutable artifact key already contains different content")
        self.objects[key] = content
        return sha256(content).hexdigest()


def execution(side: BacktestSide, day: date, price: str) -> BacktestExecutionInput:
    return BacktestExecutionInput(
        security_id="sh600000", signal_date=date(2026, 1, 2), execution_date=day,
        side=side, requested_quantity=Decimal(100), execution_price=Decimal(price),
    )


def test_model_and_backtest_artifacts_are_content_addressed_and_idempotent() -> None:
    writer = Writer()
    publisher = ResearchArtifactPublisher(writer, "minio://artifacts")
    model = LinearBaselineModel(
        model_id="baseline", model_version="v1", data_version_id="data-v1",
        factor_id="price.momentum.2d", intercept=Decimal(0), coefficient=Decimal(1),
        training_row_count=2, canonical_content_hash="a" * 64,
    )
    first_model = publisher.publish_model(model)
    second_model = publisher.publish_model(model)
    assert first_model == second_model
    report = run_portfolio_backtest(
        (
            RoundTripTrade(
                trade_id="t1",
                buy=execution(BacktestSide.BUY, date(2026, 1, 3), "10"),
                sell=execution(BacktestSide.SELL, date(2026, 1, 4), "11"),
            ),
        ),
        CostModelDefinition(
            version="cost-v1", commission_rate=Decimal(0), stamp_tax_rate=Decimal(0),
            slippage_bps=Decimal(0), minimum_commission=Decimal(0),
        ),
    )
    artifact = publisher.publish_backtest("run-001", report)
    assert artifact.artifact.uri.startswith("minio://artifacts/quant-research/backtests/run-001/")
    assert len(writer.objects) == 2
