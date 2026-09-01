from datetime import UTC, datetime
from decimal import Decimal

import pytest

from quant_research.strategy import (
    DailyStrategySnapshot,
    InMemoryStrategyOutbox,
    InMemoryStrategyPublicationStore,
    InMemoryStrategyRegistry,
    InMemoryStrategySnapshotRepository,
    LowTurnoverTopKStrategy,
    MultiFactorQualityStrategy,
    NoRebalanceStrategy,
    RebalanceDecision,
    RebalancePolicy,
    RegimeOverlayStrategy,
    StrategyContext,
    StrategyEvaluation,
    StrategyGateInput,
    StrategyOutboxEvent,
    StrategyPluginManifest,
    StrategyRunService,
    StrategyRunStatus,
    StrategyStatus,
    StrategyVersion,
    build_strategy_snapshot,
    evaluate_strategy_gates,
)


def _version(status: StrategyStatus = StrategyStatus.CANDIDATE) -> StrategyVersion:
    return StrategyVersion(
        strategy_id="no-rebalance", version="v1", code_hash="a" * 64, parameter_set_id="default",
        status=status, rebalance_policy=RebalancePolicy(minimum_holding_days=1, cooldown_trading_days=1, maximum_expected_turnover=Decimal("0.2")),
    )


def _context() -> StrategyContext:
    moment = datetime(2026, 9, 1, 1, tzinfo=UTC)
    return StrategyContext(run_id="run-1", strategy_id="no-rebalance", strategy_version="v1", parameter_set_id="default", market="CN", as_of=moment, decision_available_at=moment, data_version="dv-1", universe_version="u-1", portfolio_snapshot_id="portfolio-1", random_seed=7)


def test_candidate_cannot_publish_and_active_requires_approval() -> None:
    registry = InMemoryStrategyRegistry()
    registry.register(_version())
    with pytest.raises(ValueError, match="only ACTIVE"):
        build_strategy_snapshot(_context(), _version(), NoRebalanceStrategy().generate(_context()), datetime(2026, 9, 1, 2, tzinfo=UTC), datetime(2026, 9, 2, tzinfo=UTC), "cost-v1")
    with pytest.raises(ValueError, match="out-of-sample"):
        registry.activate("no-rebalance", "v1", StrategyEvaluation(strategy_id="no-rebalance", strategy_version="v1", out_of_sample=False, cost_model_version="cost-v1"))
    active = registry.activate("no-rebalance", "v1", StrategyEvaluation(strategy_id="no-rebalance", strategy_version="v1", out_of_sample=True, cost_model_version="cost-v1", approval_reference="approval-1"))
    assert active.status is StrategyStatus.ACTIVE


def test_no_rebalance_snapshot_is_deterministic_and_has_no_order_fields() -> None:
    registry = InMemoryStrategyRegistry()
    registry.register(_version())
    active = registry.activate("no-rebalance", "v1", StrategyEvaluation(strategy_id="no-rebalance", strategy_version="v1", out_of_sample=True, cost_model_version="cost-v1", approval_reference="approval-1"))
    context = _context()
    result = NoRebalanceStrategy().generate(context)
    snapshot = build_strategy_snapshot(context, active, result, datetime(2026, 9, 1, 2, tzinfo=UTC), datetime(2026, 9, 2, tzinfo=UTC), "cost-v1")
    assert snapshot.rebalance_decision is RebalanceDecision.NO_REBALANCE
    assert snapshot.proposed_changes == ()
    assert len(snapshot.content_hash) == 64
    repo = InMemoryStrategySnapshotRepository()
    repo.publish_atomically(snapshot)
    repo.publish_atomically(snapshot)
    assert repo.get(snapshot.snapshot_id) == snapshot


def test_plugin_context_rejects_future_decision_time_and_non_utc() -> None:
    with pytest.raises(ValueError, match="precede"):
        StrategyContext(**{**_context().model_dump(), "decision_available_at": datetime(2026, 8, 31, 23, tzinfo=UTC)})
    with pytest.raises(ValueError, match="UTC"):
        StrategyContext(**{**_context().model_dump(), "as_of": datetime.fromisoformat("2026-09-01T01:00:00")})


def test_snapshot_schema_does_not_accept_order_payload() -> None:
    with pytest.raises(ValueError):
        DailyStrategySnapshot.model_validate({"snapshot_id": "x", "order": {}})


def test_low_turnover_topk_is_deterministic_and_respects_threshold() -> None:
    base = _context().model_copy(update={
        "strategy_id": "low-turnover-topk",
        "parameters": {"scores": {"sz.000002": "2", "sz.000001": "3", "sz.000003": "1"}, "top_k": 2, "current_weights": {"sz.000001": "0.5", "sz.000002": "0.5"}},
    })
    result = LowTurnoverTopKStrategy().generate(base)
    assert result.rebalance_decision is RebalanceDecision.NO_REBALANCE
    assert [item.security_id for item in result.scores] == ["sz.000001", "sz.000002", "sz.000003"]
    changed = base.model_copy(update={"parameters": {**base.parameters, "current_weights": {"sz.000003": "1"}}})
    changed_result = LowTurnoverTopKStrategy().generate(changed)
    assert changed_result.rebalance_decision is RebalanceDecision.REBALANCE_CANDIDATE
    assert changed_result.expected_turnover == Decimal(1)


def test_low_turnover_topk_rejects_missing_scores() -> None:
    context = _context().model_copy(update={"strategy_id": "low-turnover-topk", "parameters": {}})
    with pytest.raises(ValueError, match="scores"):
        LowTurnoverTopKStrategy().generate(context)


def test_multi_factor_quality_combines_scores() -> None:
    context = _context().model_copy(update={
        "strategy_id": "multi-factor-quality",
        "parameters": {"factor_scores": {"quality": {"a": "2", "b": "1"}, "value": {"a": "1", "b": "2"}}, "factor_weights": {"quality": "0.7", "value": "0.3"}, "top_k": 1},
    })
    result = MultiFactorQualityStrategy().generate(context)
    assert result.strategy_id == "multi-factor-quality"
    assert result.target_weights[0].security_id == "a"
    assert "MULTI_FACTOR_QUALITY" in result.reason_codes


def test_regime_overlay_marks_risk_reduction_and_scales_weights() -> None:
    context = _context().model_copy(update={
        "strategy_id": "regime-overlay",
        "parameters": {"regime": "RISK_OFF", "scores": {"a": "2", "b": "1"}, "top_k": 1, "risk_off_scale": "0.5"},
    })
    result = RegimeOverlayStrategy().generate(context)
    assert result.rebalance_decision is RebalanceDecision.RISK_REDUCTION
    assert result.target_weights[0].weight == Decimal("0.5")
    with pytest.raises(ValueError, match="regime"):
        RegimeOverlayStrategy().generate(context.model_copy(update={"parameters": {"regime": "UNKNOWN", "scores": {"a": "1"}}}))


def test_untrusted_plugin_manifest_denies_external_capabilities() -> None:
    manifest = StrategyPluginManifest(strategy_id="plugin", strategy_version="v1", license="MIT")
    assert manifest.network_access is False
    assert manifest.secret_names == ()
    with pytest.raises(ValueError, match="cannot request"):
        StrategyPluginManifest(strategy_id="plugin", strategy_version="v1", license="MIT", network_access=True)
    with pytest.raises(ValueError, match="writable paths"):
        StrategyPluginManifest(strategy_id="plugin", strategy_version="v1", license="MIT", trusted=True, writable_paths=("/etc",))


def test_strategy_gates_are_auditable_and_block_activation() -> None:
    moment = datetime(2026, 9, 1, tzinfo=UTC)
    failed = evaluate_strategy_gates("no-rebalance", "v1", StrategyGateInput(pit_passed=True, out_of_sample=True, cost_model_version="cost-v1", expected_turnover=Decimal("0.4"), maximum_turnover=Decimal("0.2"), capacity_passed=False, license_passed=True, security_passed=True), moment)
    assert failed.passed is False
    assert failed.failed_gates == ("TURNOVER", "CAPACITY")
    registry = InMemoryStrategyRegistry()
    registry.register(_version())
    evaluation = StrategyEvaluation(strategy_id="no-rebalance", strategy_version="v1", out_of_sample=True, cost_model_version="cost-v1", approval_reference="approval-1")
    with pytest.raises(ValueError, match="gates failed"):
        registry.activate_with_gates("no-rebalance", "v1", evaluation, failed)
    passed = evaluate_strategy_gates("no-rebalance", "v1", StrategyGateInput(pit_passed=True, out_of_sample=True, cost_model_version="cost-v1", expected_turnover=Decimal("0.1"), maximum_turnover=Decimal("0.2"), capacity_passed=True, license_passed=True, security_passed=True), moment)
    assert registry.activate_with_gates("no-rebalance", "v1", evaluation, passed).status is StrategyStatus.ACTIVE


def test_outbox_is_idempotent_and_marks_events_published() -> None:
    outbox = InMemoryStrategyOutbox()
    event = StrategyOutboxEvent(event_id="event-1", subject="stock.quant.daily-strategy.published.v1", payload={"snapshotId": "snapshot-1"})
    outbox.append(event)
    outbox.append(event)
    assert outbox.pending() == (event,)
    outbox.mark_published("event-1", datetime(2026, 9, 1, tzinfo=UTC))
    assert outbox.pending() == ()
    with pytest.raises(ValueError, match="UTC"):
        outbox.mark_published("event-1", datetime.fromisoformat("2026-09-01T00:00:00"))
    with pytest.raises(ValueError, match="different content"):
        outbox.append(event.model_copy(update={"payload": {"snapshotId": "other"}}))


def test_snapshot_and_outbox_publication_requires_matching_hash() -> None:
    registry = InMemoryStrategyRegistry()
    registry.register(_version())
    active = registry.activate("no-rebalance", "v1", StrategyEvaluation(strategy_id="no-rebalance", strategy_version="v1", out_of_sample=True, cost_model_version="cost-v1", approval_reference="approval-1"))
    context = _context()
    snapshot = build_strategy_snapshot(context, active, NoRebalanceStrategy().generate(context), datetime(2026, 9, 1, 2, tzinfo=UTC), datetime(2026, 9, 2, tzinfo=UTC), "cost-v1")
    store = InMemoryStrategyPublicationStore()
    event = StrategyOutboxEvent(event_id="event-snapshot-1", subject="stock.quant.daily-strategy.published.v1", payload={"snapshotId": snapshot.snapshot_id, "contentHash": snapshot.content_hash})
    store.publish(snapshot, event)
    assert store.snapshots.get(snapshot.snapshot_id) == snapshot
    assert store.outbox.pending() == (event,)
    with pytest.raises(ValueError, match="content hash"):
        store.publish(snapshot, event.model_copy(update={"event_id": "event-snapshot-2", "payload": {"snapshotId": snapshot.snapshot_id, "contentHash": "b" * 64}}))


def test_strategy_run_failure_returns_previous_snapshot_as_stale() -> None:
    registry = InMemoryStrategyRegistry()
    registry.register(_version())
    active = registry.activate("no-rebalance", "v1", StrategyEvaluation(strategy_id="no-rebalance", strategy_version="v1", out_of_sample=True, cost_model_version="cost-v1", approval_reference="approval-1"))
    context = _context()
    snapshot = build_strategy_snapshot(context, active, NoRebalanceStrategy().generate(context), datetime(2026, 9, 1, 2, tzinfo=UTC), datetime(2026, 9, 2, tzinfo=UTC), "cost-v1")
    repository = InMemoryStrategySnapshotRepository()
    repository.publish_atomically(snapshot)
    runs = StrategyRunService(repository)
    runs.start("failed-run", "no-rebalance", "v1", context.as_of.date(), context.as_of)
    failed, stale = runs.fail("failed-run", "plugin timeout", datetime(2026, 9, 1, 3, tzinfo=UTC))
    assert failed.status is StrategyRunStatus.FAILED
    assert stale is not None and stale.is_stale is True
    assert repository.latest_ready() == snapshot
