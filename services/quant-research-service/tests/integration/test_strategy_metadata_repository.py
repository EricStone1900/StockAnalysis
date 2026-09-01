import os
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from quant_research.strategy import (
    InMemoryStrategyRegistry,
    NoRebalanceStrategy,
    PostgresStrategyMetadataRepository,
    RebalancePolicy,
    StrategyContext,
    StrategyEvaluation,
    StrategyOutboxEvent,
    StrategyRun,
    StrategyRunStatus,
    StrategyStatus,
    StrategyVersion,
    build_strategy_snapshot,
)

pytestmark = pytest.mark.skipif("MARKET_DATA_DATABASE_URL" not in os.environ, reason="requires local PostgreSQL")


def test_postgres_snapshot_and_outbox_are_atomic_and_idempotent() -> None:
    import psycopg

    url = os.environ["MARKET_DATA_DATABASE_URL"]
    repository = PostgresStrategyMetadataRepository(url)
    repository.migrate(str(Path(__file__).parents[2] / "migrations/002_strategy_metadata.sql"))
    registry = InMemoryStrategyRegistry()
    version = StrategyVersion(strategy_id="no-rebalance", version="integration-v1", code_hash="a" * 64, parameter_set_id="default", status=StrategyStatus.CANDIDATE, rebalance_policy=RebalancePolicy(minimum_holding_days=1, cooldown_trading_days=1, maximum_expected_turnover=Decimal("0.2")))
    registry.register(version)
    active = registry.activate("no-rebalance", "integration-v1", StrategyEvaluation(strategy_id="no-rebalance", strategy_version="integration-v1", out_of_sample=True, cost_model_version="cost-v1", approval_reference="approval"))
    moment = datetime(2026, 9, 1, tzinfo=UTC)
    context = StrategyContext(run_id="integration-strategy-run", strategy_id="no-rebalance", strategy_version=active.version, parameter_set_id="default", market="CN", as_of=moment, decision_available_at=moment, data_version="dv", universe_version="u", portfolio_snapshot_id="p", random_seed=1)
    snapshot = build_strategy_snapshot(context, active, NoRebalanceStrategy().generate(context), moment, datetime(2026, 9, 2, tzinfo=UTC), "cost-v1")
    event = StrategyOutboxEvent(event_id="integration-strategy-event", subject="stock.quant.daily-strategy.published.v1", payload={"snapshotId": snapshot.snapshot_id, "contentHash": snapshot.content_hash})
    repository.publish_snapshot_with_outbox(snapshot, event)
    repository.publish_snapshot_with_outbox(snapshot, event)
    assert repository.get_snapshot(snapshot.snapshot_id) == snapshot
    run = StrategyRun(run_id="integration-strategy-run", strategy_id="no-rebalance", strategy_version=active.version, as_of_date=date(2026, 9, 1), status=StrategyRunStatus.READY, started_at=moment, completed_at=moment, snapshot_id=snapshot.snapshot_id)
    repository.save_run(run)
    repository.save_run(run)
    assert repository.get_run(run.run_id) == run
    assert repository.pending_outbox(10) == (event,)
    repository.mark_outbox_published(event.event_id, datetime(2026, 9, 1, 3, tzinfo=UTC))
    assert repository.pending_outbox(10) == ()
    with pytest.raises(ValueError, match="not bound"):
        repository.publish_snapshot_with_outbox(snapshot, event.model_copy(update={"event_id": "integration-strategy-event-2", "payload": {"snapshotId": snapshot.snapshot_id, "contentHash": "b" * 64}}))
    with psycopg.connect(url) as connection:
        connection.execute("DELETE FROM strategy_metadata_records WHERE record_id=%s", (snapshot.snapshot_id,))
        connection.execute("DELETE FROM strategy_outbox_events WHERE event_id=%s", (event.event_id,))
        connection.execute("DELETE FROM strategy_runs WHERE run_id=%s", (run.run_id,))
