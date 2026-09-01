from datetime import UTC, datetime
from decimal import Decimal

import pytest

from quant_research.daily_analysis import DailyAnalysisInput, DataQualityStatus
from quant_research.strategy import (
    InMemoryStrategyOutbox,
    StrategyOutboxDispatcher,
    StrategyOutboxEvent,
    StrategyPluginManifest,
)


def test_future_data_is_rejected_by_strategy_context() -> None:
    from quant_research.strategy import StrategyContext

    with pytest.raises(ValueError, match="precede"):
        StrategyContext(run_id="r", strategy_id="s", strategy_version="v1", parameter_set_id="p", market="CN", as_of=datetime(2026, 9, 1, tzinfo=UTC), decision_available_at=datetime(2026, 8, 31, tzinfo=UTC), data_version="d", universe_version="u", portfolio_snapshot_id="p", random_seed=1)


def test_bad_artifact_hash_is_rejected() -> None:
    from quant_research.domain import ArtifactRef

    with pytest.raises(ValueError, match="lowercase"):
        ArtifactRef(uri="s3://artifact", sha256="Z" * 64)


def test_duplicate_event_conflict_is_rejected() -> None:
    outbox = InMemoryStrategyOutbox()
    event = StrategyOutboxEvent(event_id="e", subject="subject", payload={"v": 1})
    outbox.append(event)
    with pytest.raises(ValueError, match="different content"):
        outbox.append(event.model_copy(update={"payload": {"v": 2}}))


def test_partial_calculation_cannot_use_failed_input() -> None:
    with pytest.raises(ValueError, match="FAIL input"):
        DailyAnalysisInput(data_version_id="d", universe_version="u", factor_set_version="f", model_version="m", quality_status=DataQualityStatus.FAIL)


def test_outbox_failure_keeps_event_pending() -> None:
    class BrokenPublisher:
        def publish(self, subject: str, payload: dict[str, object]) -> None:
            raise RuntimeError("NATS outage")

    outbox = InMemoryStrategyOutbox()
    outbox.append(StrategyOutboxEvent(event_id="e", subject="subject", payload={"v": Decimal(1)}))
    with pytest.raises(RuntimeError, match="NATS"):
        StrategyOutboxDispatcher(outbox, BrokenPublisher()).dispatch_once(datetime(2026, 9, 1, tzinfo=UTC))
    assert len(outbox.pending()) == 1


def test_untrusted_runner_isolation_is_enforced() -> None:
    with pytest.raises(ValueError, match="cannot request"):
        StrategyPluginManifest(strategy_id="runner", strategy_version="v1", license="MIT", network_access=True)
