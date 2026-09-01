from datetime import UTC, date, datetime
from decimal import Decimal

from quant_research.daily_analysis import (
    DailyAnalysisInput,
    DailyAnalysisService,
    DailyQualitySummary,
    DataQualityStatus,
    InMemoryDailyAnalysisRepository,
)
from quant_research.strategy import (
    InMemoryStrategyPublicationStore,
    InMemoryStrategyRegistry,
    NoRebalanceStrategy,
    RebalancePolicy,
    StrategyContext,
    StrategyEvaluation,
    StrategyExecutionService,
    StrategyStatus,
    StrategyVersion,
)


def test_stage03_fixture_e2e_is_reproducible() -> None:
    now = datetime(2026, 9, 1, 1, tzinfo=UTC)
    input_data = DailyAnalysisInput(data_version_id="fixture-dv-v1", universe_version="fixture-u-v1", factor_set_version="fixture-f-v1", model_version="fixture-m-v1", quality_status=DataQualityStatus.WARN)
    hashes: list[str] = []
    for index in range(2):
        daily = DailyAnalysisService(InMemoryDailyAnalysisRepository())
        daily.start("daily-fixture", date(2026, 8, 31), input_data, now)
        daily_snapshot = daily.publish("daily-fixture", (), (), DailyQualitySummary(status=DataQualityStatus.WARN, excluded_count=0), ("fixture-evidence",), now)
        registry = InMemoryStrategyRegistry()
        registry.register(StrategyVersion(strategy_id="no-rebalance", version="v1", code_hash="a" * 64, parameter_set_id="default", status=StrategyStatus.CANDIDATE, rebalance_policy=RebalancePolicy(minimum_holding_days=1, cooldown_trading_days=1, maximum_expected_turnover=Decimal("0.2"))))
        active = registry.activate("no-rebalance", "v1", StrategyEvaluation(strategy_id="no-rebalance", strategy_version="v1", out_of_sample=True, cost_model_version="cost-v1", approval_reference="fixture-approval"))
        context = StrategyContext(run_id="strategy-fixture", strategy_id="no-rebalance", strategy_version=active.version, parameter_set_id="default", market="CN", as_of=now, decision_available_at=now, data_version=input_data.data_version_id, universe_version=input_data.universe_version, portfolio_snapshot_id="portfolio-fixture", random_seed=7)
        strategy_snapshot = StrategyExecutionService(registry, InMemoryStrategyPublicationStore()).execute(context, NoRebalanceStrategy(), now, datetime(2026, 9, 2, tzinfo=UTC), "cost-v1")
        hashes.append(f"{daily_snapshot.canonical_content_hash}:{strategy_snapshot.content_hash}")
    assert hashes[0] == hashes[1]
