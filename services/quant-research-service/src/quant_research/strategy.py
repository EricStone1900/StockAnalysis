"""日频策略 Registry 与 strategy-plugin/v1 最小 SDK。"""

from __future__ import annotations

import json
from datetime import UTC, date, datetime
from decimal import Decimal
from enum import StrEnum
from hashlib import sha256
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, Field, model_validator

from quant_research.domain import ArtifactRef


class StrategyStatus(StrEnum):
    DRAFT = "DRAFT"
    CANDIDATE = "CANDIDATE"
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    RETIRED = "RETIRED"


class StrategyRunStatus(StrEnum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    READY = "READY"
    FAILED = "FAILED"


class StrategyRun(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    run_id: str
    strategy_id: str
    strategy_version: str
    as_of_date: date
    status: StrategyRunStatus
    started_at: datetime
    completed_at: datetime | None = None
    snapshot_id: str | None = None
    failure_reason: str | None = None

    @model_validator(mode="after")
    def validate_run(self) -> StrategyRun:
        for value in (self.started_at, self.completed_at):
            if value is not None and (value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value)):
                raise ValueError("strategy run timestamps must use UTC")
        if self.status is StrategyRunStatus.READY and self.snapshot_id is None:
            raise ValueError("READY strategy run requires snapshot_id")
        if self.status is StrategyRunStatus.FAILED and not self.failure_reason:
            raise ValueError("FAILED strategy run requires failure_reason")
        return self


class RebalanceDecision(StrEnum):
    NO_REBALANCE = "NO_REBALANCE"
    REBALANCE_CANDIDATE = "REBALANCE_CANDIDATE"
    RISK_REDUCTION = "RISK_REDUCTION"


class RebalancePolicy(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    evaluation_frequency: str = "DAILY"
    minimum_holding_days: int = Field(ge=0)
    cooldown_trading_days: int = Field(ge=0)
    maximum_expected_turnover: Decimal = Field(ge=0, le=1)


class StrategyDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    strategy_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    description: str = Field(min_length=1)


class StrategyVersion(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    strategy_id: str = Field(min_length=1)
    version: str = Field(min_length=1)
    code_hash: str = Field(min_length=64, max_length=64)
    parameter_set_id: str = Field(min_length=1)
    status: StrategyStatus = StrategyStatus.DRAFT
    rebalance_policy: RebalancePolicy

    @model_validator(mode="after")
    def validate_hash(self) -> StrategyVersion:
        if any(c not in "0123456789abcdef" for c in self.code_hash):
            raise ValueError("code_hash must be lowercase SHA-256")
        return self


class StrategyEvaluation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    strategy_id: str
    strategy_version: str
    out_of_sample: bool
    cost_model_version: str
    approval_reference: str | None = None


class StrategyPluginManifest(BaseModel):
    """插件声明；默认拒绝所有外部能力。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    api_version: str = "strategy-plugin/v1"
    kind: str = "DailyStrategyPlugin"
    strategy_id: str = Field(min_length=1)
    strategy_version: str = Field(min_length=1)
    trusted: bool = False
    network_access: bool = False
    database_access: bool = False
    secret_names: tuple[str, ...] = ()
    writable_paths: tuple[str, ...] = ()
    license: str = Field(min_length=1)

    @model_validator(mode="after")
    def enforce_isolation_defaults(self) -> StrategyPluginManifest:
        if self.api_version != "strategy-plugin/v1" or self.kind != "DailyStrategyPlugin":
            raise ValueError("unsupported strategy plugin manifest")
        if not self.trusted and (self.network_access or self.database_access or self.secret_names or self.writable_paths):
            raise ValueError("untrusted plugins cannot request network, database, secrets or writable paths")
        if any(path.startswith("/") and path not in {"/tmp"} for path in self.writable_paths):
            raise ValueError("plugin writable paths must be restricted")
        return self


class StrategyGateInput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    pit_passed: bool
    out_of_sample: bool
    cost_model_version: str = Field(min_length=1)
    expected_turnover: Decimal = Field(ge=0, le=1)
    maximum_turnover: Decimal = Field(ge=0, le=1)
    capacity_passed: bool
    license_passed: bool
    security_passed: bool


class StrategyGateResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    strategy_id: str
    strategy_version: str
    passed: bool
    failed_gates: tuple[str, ...] = ()
    evaluated_at: datetime


class StrategyOutboxEvent(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    event_id: str = Field(min_length=1)
    subject: str = Field(min_length=1)
    payload: dict[str, Any]
    published_at: datetime | None = None

    @model_validator(mode="after")
    def validate_event(self) -> StrategyOutboxEvent:
        if self.published_at is not None and (self.published_at.tzinfo is None or self.published_at.utcoffset() != UTC.utcoffset(self.published_at)):
            raise ValueError("published_at must use UTC")
        return self


class InMemoryStrategyOutbox:
    def __init__(self) -> None:
        self._events: dict[str, str] = {}

    def append(self, event: StrategyOutboxEvent) -> None:
        payload = _canonical(event)
        if event.event_id in self._events and self._events[event.event_id] != payload:
            raise ValueError("outbox event id already contains different content")
        self._events[event.event_id] = payload

    def pending(self) -> tuple[StrategyOutboxEvent, ...]:
        return tuple(event for value in self._events.values() if (event := StrategyOutboxEvent.model_validate_json(value)).published_at is None)

    def mark_published(self, event_id: str, published_at: datetime) -> None:
        if published_at.tzinfo is None or published_at.utcoffset() != UTC.utcoffset(published_at):
            raise ValueError("published_at must use UTC")
        event = next((item for item in self.pending() if item.event_id == event_id), None)
        if event is None:
            return
        self._events[event_id] = _canonical(event.model_copy(update={"published_at": published_at}))


class StrategyEventPublisher(Protocol):
    def publish(self, subject: str, payload: dict[str, Any]) -> None: ...


class StrategyOutboxDispatcher:
    """一次投递一个事件；异常时保持pending，下一次可安全重试。"""

    def __init__(self, outbox: InMemoryStrategyOutbox, publisher: StrategyEventPublisher) -> None:
        self._outbox = outbox
        self._publisher = publisher

    def dispatch_once(self, now: datetime) -> StrategyOutboxEvent | None:
        if now.tzinfo is None or now.utcoffset() != UTC.utcoffset(now):
            raise ValueError("dispatch timestamp must use UTC")
        pending = self._outbox.pending()
        if not pending:
            return None
        event = pending[0]
        self._publisher.publish(event.subject, event.payload)
        self._outbox.mark_published(event.event_id, now)
        return event


class PostgresStrategyOutboxDispatcher:
    """PostgreSQL Outbox 投递器；发布异常时不写确认时间。"""

    def __init__(self, repository: PostgresStrategyMetadataRepository, publisher: StrategyEventPublisher) -> None:
        self._repository = repository
        self._publisher = publisher

    def dispatch_once(self, now: datetime) -> StrategyOutboxEvent | None:
        pending = self._repository.pending_outbox(1)
        if not pending:
            return None
        event = pending[0]
        self._publisher.publish(event.subject, event.payload)
        self._repository.mark_outbox_published(event.event_id, now)
        return event


class InMemoryStrategyPublicationStore:
    """Fixture事务存储：快照和Outbox事件要么同时写入，要么均不改变。"""

    def __init__(self) -> None:
        self.snapshots = InMemoryStrategySnapshotRepository()
        self.outbox = InMemoryStrategyOutbox()

    def publish(self, snapshot: DailyStrategySnapshot, event: StrategyOutboxEvent) -> None:
        if event.subject != "stock.quant.daily-strategy.published.v1" or event.payload.get("snapshotId") != snapshot.snapshot_id:
            raise ValueError("outbox event is not bound to the strategy snapshot")
        if event.payload.get("contentHash") != snapshot.content_hash:
            raise ValueError("outbox event content hash does not match snapshot")
        self.snapshots.publish_atomically(snapshot)
        self.outbox.append(event)


class StrategyExecutionService:
    """Fixture端到端协调器：只运行已激活策略并发布研究快照。"""

    def __init__(self, registry: InMemoryStrategyRegistry, publication: InMemoryStrategyPublicationStore) -> None:
        self._registry = registry
        self._publication = publication

    def execute(self, context: StrategyContext, plugin: StrategyPlugin, published_at: datetime, valid_until: datetime, cost_model_version: str) -> DailyStrategySnapshot:
        version = self._registry.get(context.strategy_id, context.strategy_version)
        if version is None or version.status is not StrategyStatus.ACTIVE:
            raise ValueError("strategy version is not ACTIVE")
        plugin.validate_context(context)
        result = plugin.generate(context)
        snapshot = build_strategy_snapshot(context, version, result, published_at, valid_until, cost_model_version)
        event = StrategyOutboxEvent(event_id=f"strategy-snapshot-published-{snapshot.snapshot_id}", subject="stock.quant.daily-strategy.published.v1", payload={"snapshotId": snapshot.snapshot_id, "runId": snapshot.run_id, "contentHash": snapshot.content_hash})
        self._publication.publish(snapshot, event)
        return snapshot


def evaluate_strategy_gates(strategy_id: str, strategy_version: str, gates: StrategyGateInput, evaluated_at: datetime) -> StrategyGateResult:
    if evaluated_at.tzinfo is None or evaluated_at.utcoffset() != UTC.utcoffset(evaluated_at):
        raise ValueError("evaluated_at must use UTC")
    failed: list[str] = []
    if not gates.pit_passed:
        failed.append("PIT")
    if not gates.out_of_sample:
        failed.append("OUT_OF_SAMPLE")
    if gates.expected_turnover > gates.maximum_turnover:
        failed.append("TURNOVER")
    if not gates.capacity_passed:
        failed.append("CAPACITY")
    if not gates.license_passed:
        failed.append("LICENSE")
    if not gates.security_passed:
        failed.append("SECURITY")
    return StrategyGateResult(strategy_id=strategy_id, strategy_version=strategy_version, passed=not failed, failed_gates=tuple(failed), evaluated_at=evaluated_at)


class StrategyContext(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    api_version: str = "strategy-plugin/v1"
    run_id: str
    strategy_id: str
    strategy_version: str
    parameter_set_id: str
    market: str
    as_of: datetime
    decision_available_at: datetime
    data_version: str
    universe_version: str
    factor_set_version: str | None = None
    model_version: str | None = None
    portfolio_snapshot_id: str
    input_artifacts: tuple[ArtifactRef, ...] = ()
    parameters: dict[str, Any] = Field(default_factory=dict)
    random_seed: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_context(self) -> StrategyContext:
        if self.api_version != "strategy-plugin/v1":
            raise ValueError("unsupported strategy plugin API version")
        for value in (self.as_of, self.decision_available_at):
            if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
                raise ValueError("strategy timestamps must use UTC")
        if self.decision_available_at < self.as_of:
            raise ValueError("decision_available_at cannot precede as_of")
        return self


class InstrumentScore(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    security_id: str
    score: Decimal


class TargetWeight(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    security_id: str
    weight: Decimal = Field(ge=0, le=1)


class ProposedPositionChange(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    security_id: str
    current_weight: Decimal = Field(ge=0, le=1)
    target_weight: Decimal = Field(ge=0, le=1)


class StrategyResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    run_id: str
    strategy_id: str
    strategy_version: str
    as_of: datetime
    rebalance_decision: RebalanceDecision
    scores: tuple[InstrumentScore, ...] = ()
    target_weights: tuple[TargetWeight, ...] = ()
    proposed_changes: tuple[ProposedPositionChange, ...] = ()
    expected_turnover: Decimal = Field(ge=0)
    estimated_transaction_cost: Decimal = Field(ge=0)
    estimated_slippage: Decimal = Field(ge=0)
    reason_codes: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    evidence_refs: tuple[ArtifactRef, ...] = ()

    @model_validator(mode="after")
    def validate_result(self) -> StrategyResult:
        if any(value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value) for value in (self.as_of,)):
            raise ValueError("strategy result timestamp must use UTC")
        if tuple(sorted(self.scores, key=lambda item: item.security_id)) != self.scores:
            raise ValueError("scores must be sorted by security_id")
        if tuple(sorted(self.target_weights, key=lambda item: item.security_id)) != self.target_weights:
            raise ValueError("target_weights must be sorted by security_id")
        return self


class StrategyPlugin(Protocol):
    def validate_context(self, context: StrategyContext) -> None: ...
    def generate(self, context: StrategyContext) -> StrategyResult: ...


class NoRebalanceStrategy:
    def validate_context(self, context: StrategyContext) -> None:
        if context.strategy_id != "no-rebalance":
            raise ValueError("context strategy does not match no-rebalance plugin")

    def generate(self, context: StrategyContext) -> StrategyResult:
        self.validate_context(context)
        return StrategyResult(
            run_id=context.run_id, strategy_id=context.strategy_id, strategy_version=context.strategy_version,
            as_of=context.as_of, rebalance_decision=RebalanceDecision.NO_REBALANCE,
            expected_turnover=Decimal(0), estimated_transaction_cost=Decimal(0), estimated_slippage=Decimal(0),
            reason_codes=("POLICY_COOLDOWN",),
        )


class LowTurnoverTopKStrategy:
    """按分数选择Top-K；变化不足时保持组合并返回NO_REBALANCE。"""

    def validate_context(self, context: StrategyContext) -> None:
        if context.strategy_id != "low-turnover-topk":
            raise ValueError("context strategy does not match low-turnover-topk plugin")
        scores = context.parameters.get("scores")
        if not isinstance(scores, dict) or not scores:
            raise ValueError("low-turnover-topk requires a non-empty scores mapping")

    def generate(self, context: StrategyContext) -> StrategyResult:
        self.validate_context(context)
        scores = context.parameters["scores"]
        top_k = int(context.parameters.get("top_k", 5))
        minimum_change = Decimal(str(context.parameters.get("minimum_signal_change", "0")))
        if top_k < 1 or top_k > len(scores):
            raise ValueError("top_k must be within the score universe")
        current = {str(key): Decimal(str(value)) for key, value in context.parameters.get("current_weights", {}).items()}
        ranked = sorted(((str(key), Decimal(str(value))) for key, value in scores.items()), key=lambda item: (-item[1], item[0]))
        selected = ranked[:top_k]
        weight = Decimal(1) / Decimal(top_k)
        targets = tuple(TargetWeight(security_id=security_id, weight=weight) for security_id, _ in sorted(selected))
        all_ids = sorted(set(current) | {item.security_id for item in targets})
        target_map = {item.security_id: item.weight for item in targets}
        changes = tuple(
            ProposedPositionChange(security_id=security_id, current_weight=current.get(security_id, Decimal(0)), target_weight=target_map.get(security_id, Decimal(0)))
            for security_id in all_ids
            if current.get(security_id, Decimal(0)) != target_map.get(security_id, Decimal(0))
        )
        turnover = sum((abs(item.target_weight - item.current_weight) for item in changes), Decimal(0)) / Decimal(2)
        decision = RebalanceDecision.NO_REBALANCE if turnover <= minimum_change else RebalanceDecision.REBALANCE_CANDIDATE
        return StrategyResult(
            run_id=context.run_id, strategy_id=context.strategy_id, strategy_version=context.strategy_version,
            as_of=context.as_of, rebalance_decision=decision,
            scores=tuple(InstrumentScore(security_id=security_id, score=score) for security_id, score in ranked),
            target_weights=targets, proposed_changes=changes, expected_turnover=turnover,
            estimated_transaction_cost=Decimal(0), estimated_slippage=Decimal(0),
            reason_codes=("TOPK_SELECTED",) if decision is not RebalanceDecision.NO_REBALANCE else ("TURNOVER_BELOW_THRESHOLD",),
        )


class MultiFactorQualityStrategy:
    """按多个已验证因子分数加权排名；不在插件内读取外部数据。"""

    def validate_context(self, context: StrategyContext) -> None:
        if context.strategy_id != "multi-factor-quality":
            raise ValueError("context strategy does not match multi-factor-quality plugin")
        factors = context.parameters.get("factor_scores")
        weights = context.parameters.get("factor_weights")
        if not isinstance(factors, dict) or not isinstance(weights, dict) or not factors or not weights:
            raise ValueError("multi-factor-quality requires factor_scores and factor_weights")
        if set(factors) != set(weights):
            raise ValueError("factor scores and weights must have the same factors")

    def generate(self, context: StrategyContext) -> StrategyResult:
        self.validate_context(context)
        factors = context.parameters["factor_scores"]
        weights = {str(k): Decimal(str(v)) for k, v in context.parameters["factor_weights"].items()}
        securities = sorted({str(security) for values in factors.values() for security in values})
        combined = {
            security: sum((Decimal(str(factors[factor].get(security, 0))) * weight for factor, weight in weights.items()), Decimal(0))
            for security in securities
        }
        params = {"scores": combined, "top_k": context.parameters.get("top_k", 5), "current_weights": context.parameters.get("current_weights", {}), "minimum_signal_change": context.parameters.get("minimum_signal_change", "0")}
        delegated = context.model_copy(update={"strategy_id": "low-turnover-topk", "parameters": params})
        result = LowTurnoverTopKStrategy().generate(delegated)
        return result.model_copy(update={"strategy_id": context.strategy_id, "strategy_version": context.strategy_version, "reason_codes": ("MULTI_FACTOR_QUALITY",) + result.reason_codes})


class RegimeOverlayStrategy:
    """在高风险市场状态下将目标权重缩放为风险减仓，不改变数据事实。"""

    def validate_context(self, context: StrategyContext) -> None:
        if context.strategy_id != "regime-overlay":
            raise ValueError("context strategy does not match regime-overlay plugin")
        if context.parameters.get("regime") not in {"NORMAL", "RISK_OFF"}:
            raise ValueError("regime must be NORMAL or RISK_OFF")

    def generate(self, context: StrategyContext) -> StrategyResult:
        self.validate_context(context)
        base_scores = context.parameters.get("scores", {})
        if not isinstance(base_scores, dict) or not base_scores:
            raise ValueError("regime-overlay requires scores")
        delegated = context.model_copy(update={"strategy_id": "low-turnover-topk", "parameters": {**context.parameters, "scores": base_scores}})
        result = LowTurnoverTopKStrategy().generate(delegated)
        if context.parameters["regime"] != "RISK_OFF":
            return result.model_copy(update={"strategy_id": context.strategy_id, "reason_codes": ("REGIME_NORMAL",) + result.reason_codes})
        scale = Decimal(str(context.parameters.get("risk_off_scale", "0.5")))
        if scale < 0 or scale > 1:
            raise ValueError("risk_off_scale must be between 0 and 1")
        targets = tuple(item.model_copy(update={"weight": item.weight * scale}) for item in result.target_weights)
        changes = tuple(item.model_copy(update={"target_weight": item.target_weight * scale}) for item in result.proposed_changes)
        return result.model_copy(update={"strategy_id": context.strategy_id, "target_weights": targets, "proposed_changes": changes, "rebalance_decision": RebalanceDecision.RISK_REDUCTION, "reason_codes": ("REGIME_RISK_OFF",)})


class InMemoryStrategyRegistry:
    def __init__(self) -> None:
        self._versions: dict[tuple[str, str], StrategyVersion] = {}

    def register(self, version: StrategyVersion) -> None:
        key = (version.strategy_id, version.version)
        if key in self._versions and self._versions[key] != version:
            raise ValueError("strategy version already contains different content")
        self._versions[key] = version

    def activate(self, strategy_id: str, version: str, evaluation: StrategyEvaluation) -> StrategyVersion:
        current = self._versions.get((strategy_id, version))
        if current is None:
            raise ValueError("strategy version not found")
        if current.status is not StrategyStatus.CANDIDATE:
            raise ValueError("only CANDIDATE strategy versions can be activated")
        if not evaluation.out_of_sample or evaluation.approval_reference is None:
            raise ValueError("ACTIVE strategy requires out-of-sample evaluation and approval")
        activated = current.model_copy(update={"status": StrategyStatus.ACTIVE})
        self._versions[(strategy_id, version)] = activated
        return activated

    def activate_with_gates(self, strategy_id: str, version: str, evaluation: StrategyEvaluation, gates: StrategyGateResult) -> StrategyVersion:
        if not gates.passed:
            raise ValueError(f"strategy gates failed: {','.join(gates.failed_gates)}")
        if gates.strategy_id != strategy_id or gates.strategy_version != version:
            raise ValueError("strategy gate result does not match version")
        return self.activate(strategy_id, version, evaluation)

    def get(self, strategy_id: str, version: str) -> StrategyVersion | None:
        return self._versions.get((strategy_id, version))


class DailyStrategySnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    snapshot_id: str
    run_id: str
    strategy_id: str
    strategy_version: str
    parameter_set_id: str
    as_of_date: date
    published_at: datetime
    valid_until: datetime
    data_version: str
    universe_version: str
    portfolio_snapshot_id: str
    cost_model_version: str
    rebalance_decision: RebalanceDecision
    current_weights: tuple[TargetWeight, ...] = ()
    target_weights: tuple[TargetWeight, ...] = ()
    proposed_changes: tuple[ProposedPositionChange, ...] = ()
    expected_turnover: Decimal = Field(ge=0)
    estimated_transaction_cost: Decimal = Field(ge=0)
    estimated_slippage: Decimal = Field(ge=0)
    reason_codes: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    evidence_ids: tuple[str, ...] = ()
    content_hash: str = Field(min_length=64, max_length=64)
    is_stale: bool = False


class InMemoryStrategySnapshotRepository:
    def __init__(self) -> None:
        self._items: dict[str, str] = {}
        self._latest_id: str | None = None

    def publish_atomically(self, snapshot: DailyStrategySnapshot) -> None:
        payload = _canonical(snapshot)
        if snapshot.snapshot_id in self._items and self._items[snapshot.snapshot_id] != payload:
            raise ValueError("strategy snapshot id already contains different content")
        self._items[snapshot.snapshot_id] = payload
        if not snapshot.is_stale:
            self._latest_id = snapshot.snapshot_id

    def get(self, snapshot_id: str) -> DailyStrategySnapshot | None:
        payload = self._items.get(snapshot_id)
        return None if payload is None else DailyStrategySnapshot.model_validate_json(payload)

    def latest_ready(self) -> DailyStrategySnapshot | None:
        return None if self._latest_id is None else self.get(self._latest_id)


class StrategyRunService:
    def __init__(self, snapshots: InMemoryStrategySnapshotRepository) -> None:
        self._snapshots = snapshots
        self._runs: dict[str, StrategyRun] = {}

    def start(self, run_id: str, strategy_id: str, strategy_version: str, as_of_date: date, started_at: datetime) -> StrategyRun:
        if started_at.tzinfo is None or started_at.utcoffset() != UTC.utcoffset(started_at):
            raise ValueError("started_at must use UTC")
        existing = self._runs.get(run_id)
        if existing is not None:
            if (existing.strategy_id, existing.strategy_version, existing.as_of_date) != (strategy_id, strategy_version, as_of_date):
                raise ValueError("run id already contains different strategy input")
            return existing
        run = StrategyRun(run_id=run_id, strategy_id=strategy_id, strategy_version=strategy_version, as_of_date=as_of_date, status=StrategyRunStatus.RUNNING, started_at=started_at)
        self._runs[run_id] = run
        return run

    def ready(self, run_id: str, snapshot_id: str, completed_at: datetime) -> StrategyRun:
        run = self._runs.get(run_id)
        if run is None or run.status is not StrategyRunStatus.RUNNING:
            raise ValueError("strategy run is not running")
        if completed_at.tzinfo is None or completed_at.utcoffset() != UTC.utcoffset(completed_at):
            raise ValueError("completed_at must use UTC")
        updated = run.model_copy(update={"status": StrategyRunStatus.READY, "snapshot_id": snapshot_id, "completed_at": completed_at})
        self._runs[run_id] = updated
        return updated

    def fail(self, run_id: str, reason: str, completed_at: datetime) -> tuple[StrategyRun, DailyStrategySnapshot | None]:
        run = self._runs.get(run_id)
        if run is None:
            raise ValueError("strategy run not found")
        updated = run.model_copy(update={"status": StrategyRunStatus.FAILED, "failure_reason": reason, "completed_at": completed_at})
        self._runs[run_id] = updated
        previous = self._snapshots.latest_ready()
        return updated, None if previous is None else previous.model_copy(update={"snapshot_id": f"{previous.snapshot_id}-stale", "is_stale": True})

    def get(self, run_id: str) -> StrategyRun | None:
        return self._runs.get(run_id)


class PostgresStrategyMetadataRepository:
    """策略版本与快照的 JSONB 元数据仓储；大对象仍只保存 Artifact 引用。"""

    def __init__(self, database_url: str) -> None:
        self._database_url = database_url

    def migrate(self, migration_path: str) -> None:
        import psycopg

        with psycopg.connect(self._database_url, autocommit=True) as connection, open(migration_path, encoding="utf-8") as migration:
            connection.execute(migration.read())

    def save_version(self, version: StrategyVersion) -> None:
        self._save("strategy_version", f"{version.strategy_id}:{version.version}", version)

    def get_version(self, strategy_id: str, version: str) -> StrategyVersion | None:
        value = self._get("strategy_version", f"{strategy_id}:{version}")
        return None if value is None else StrategyVersion.model_validate(value)

    def get(self, snapshot_id: str) -> DailyStrategySnapshot | None:
        return self.get_snapshot(snapshot_id)

    def save_gate(self, gate: StrategyGateResult) -> None:
        self._save("strategy_gate", f"{gate.strategy_id}:{gate.strategy_version}", gate)

    def save_snapshot(self, snapshot: DailyStrategySnapshot) -> None:
        self._save("strategy_snapshot", snapshot.snapshot_id, snapshot)

    def get_snapshot(self, snapshot_id: str) -> DailyStrategySnapshot | None:
        value = self._get("strategy_snapshot", snapshot_id)
        return None if value is None else DailyStrategySnapshot.model_validate(value)

    def append_outbox(self, event: StrategyOutboxEvent) -> None:
        import psycopg

        payload = _canonical(event)
        with psycopg.connect(self._database_url) as connection:
            row = connection.execute("SELECT subject, payload::text FROM strategy_outbox_events WHERE event_id=%s", (event.event_id,)).fetchone()
            if row is not None:
                if str(row[0]) != event.subject or _canonical(json.loads(str(row[1]))) != payload:
                    raise ValueError("outbox event id already contains different content")
                return
            connection.execute("INSERT INTO strategy_outbox_events(event_id, subject, payload) VALUES (%s,%s,%s::jsonb)", (event.event_id, event.subject, payload))

    def publish_snapshot_with_outbox(self, snapshot: DailyStrategySnapshot, event: StrategyOutboxEvent) -> None:
        """同一数据库事务写入快照和事件；冲突时整体回滚。"""
        import psycopg

        if event.subject != "stock.quant.daily-strategy.published.v1" or event.payload.get("snapshotId") != snapshot.snapshot_id or event.payload.get("contentHash") != snapshot.content_hash:
            raise ValueError("outbox event is not bound to the strategy snapshot")
        snapshot_payload = _canonical(snapshot)
        event_payload = _canonical(event)
        with psycopg.connect(self._database_url) as connection:
            snapshot_row = connection.execute("SELECT payload::text FROM strategy_metadata_records WHERE record_type='strategy_snapshot' AND record_id=%s", (snapshot.snapshot_id,)).fetchone()
            if snapshot_row is not None and _canonical(json.loads(str(snapshot_row[0]))) != snapshot_payload:
                raise ValueError("strategy snapshot already contains different content")
            event_row = connection.execute("SELECT subject, payload::text FROM strategy_outbox_events WHERE event_id=%s", (event.event_id,)).fetchone()
            if event_row is not None and (str(event_row[0]) != event.subject or _canonical(json.loads(str(event_row[1]))) != event_payload):
                raise ValueError("outbox event id already contains different content")
            if snapshot_row is None:
                connection.execute("INSERT INTO strategy_metadata_records(record_type, record_id, payload) VALUES ('strategy_snapshot',%s,%s::jsonb)", (snapshot.snapshot_id, snapshot_payload))
            if event_row is None:
                connection.execute("INSERT INTO strategy_outbox_events(event_id, subject, payload) VALUES (%s,%s,%s::jsonb)", (event.event_id, event.subject, event_payload))

    def pending_outbox(self, limit: int = 100) -> tuple[StrategyOutboxEvent, ...]:
        if limit < 1:
            raise ValueError("limit must be positive")
        import psycopg

        with psycopg.connect(self._database_url) as connection:
            rows = connection.execute("SELECT payload::text FROM strategy_outbox_events WHERE published_at IS NULL ORDER BY created_at, event_id LIMIT %s", (limit,)).fetchall()
        return tuple(StrategyOutboxEvent.model_validate_json(str(row[0])) for row in rows)

    def mark_outbox_published(self, event_id: str, published_at: datetime) -> None:
        if published_at.tzinfo is None or published_at.utcoffset() != UTC.utcoffset(published_at):
            raise ValueError("published_at must use UTC")
        import psycopg

        with psycopg.connect(self._database_url) as connection:
            connection.execute("UPDATE strategy_outbox_events SET published_at=%s WHERE event_id=%s AND published_at IS NULL", (published_at, event_id))

    def _save(self, record_type: str, record_id: str, value: object) -> None:
        import psycopg

        payload = _canonical(value)
        with psycopg.connect(self._database_url) as connection:
            row = connection.execute("SELECT payload::text FROM strategy_metadata_records WHERE record_type=%s AND record_id=%s", (record_type, record_id)).fetchone()
            if row is not None:
                if _canonical(json.loads(str(row[0]))) != payload:
                    raise ValueError("strategy metadata record contains different content")
                return
            connection.execute("INSERT INTO strategy_metadata_records(record_type, record_id, payload) VALUES (%s,%s,%s::jsonb)", (record_type, record_id, payload))

    def _get(self, record_type: str, record_id: str) -> dict[str, Any] | None:
        import psycopg

        with psycopg.connect(self._database_url) as connection:
            row = connection.execute("SELECT payload::text FROM strategy_metadata_records WHERE record_type=%s AND record_id=%s", (record_type, record_id)).fetchone()
        return None if row is None else json.loads(str(row[0]))


def build_strategy_snapshot(context: StrategyContext, version: StrategyVersion, result: StrategyResult, published_at: datetime, valid_until: datetime, cost_model_version: str) -> DailyStrategySnapshot:
    if version.status is not StrategyStatus.ACTIVE:
        raise ValueError("only ACTIVE strategy versions can publish production snapshots")
    if result.run_id != context.run_id or result.strategy_id != context.strategy_id or result.strategy_version != version.version:
        raise ValueError("strategy result does not match context or version")
    snapshot = DailyStrategySnapshot(
        snapshot_id=f"daily-strategy-{context.run_id}", run_id=context.run_id, strategy_id=context.strategy_id,
        strategy_version=version.version, parameter_set_id=context.parameter_set_id, as_of_date=context.as_of.date(),
        published_at=published_at, valid_until=valid_until, data_version=context.data_version,
        universe_version=context.universe_version, portfolio_snapshot_id=context.portfolio_snapshot_id,
        cost_model_version=cost_model_version, rebalance_decision=result.rebalance_decision,
        target_weights=result.target_weights, proposed_changes=result.proposed_changes,
        expected_turnover=result.expected_turnover, estimated_transaction_cost=result.estimated_transaction_cost,
        estimated_slippage=result.estimated_slippage, reason_codes=result.reason_codes, warnings=result.warnings,
        evidence_ids=tuple(sorted({ref.uri for ref in result.evidence_refs})), content_hash="0" * 64,
    )
    return snapshot.model_copy(update={"content_hash": sha256(_canonical(snapshot).encode()).hexdigest()})


def _canonical(value: object) -> str:
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json")
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
