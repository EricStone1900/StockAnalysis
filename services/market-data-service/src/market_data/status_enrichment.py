import json
from collections.abc import Iterable
from datetime import UTC, date, datetime
from hashlib import sha256
from typing import Protocol

from pydantic import BaseModel

from .baostock_status import (
    BaoStockTradingStatusAdapter,
    requests_for_days,
    security_id_from_baostock,
)
from .domain import Exchange, SecurityId
from .lineage import FieldProvenance, ProvenanceRole
from .pit import RawArtifact
from .quality import QualityStatus
from .repository import SourcePolicy
from .trading_status import (
    CloseGapReconciliation,
    CloseGapReconciliationStatus,
    StatusEnrichmentMode,
    StatusEnrichmentQualityReport,
    TradingStatus,
    TradingStatusFact,
)


class ImmutableArtifactWriter(Protocol):
    def put_immutable(self, key: str, content: bytes) -> str: ...


class StatusLineageWriter(Protocol):
    def ensure_policy(self, policy: SourcePolicy) -> None: ...

    def ensure_securities(self, security_ids: Iterable[SecurityId]) -> None: ...

    def save_raw_artifact(self, artifact: RawArtifact) -> None: ...

    def save_trading_status_fact(self, fact: TradingStatusFact) -> None: ...

    def save_close_gap_reconciliation(self, reconciliation: CloseGapReconciliation, policy_version: str) -> None: ...


class CloseGap(BaseModel):
    security_id: SecurityId
    trading_day: date


class StatusEnrichmentResult(BaseModel):
    mode: StatusEnrichmentMode = StatusEnrichmentMode.EXACT
    facts: tuple[TradingStatusFact, ...]
    reconciliations: tuple[CloseGapReconciliation, ...]
    report: StatusEnrichmentQualityReport
    quality_status: QualityStatus


def _status(raw: str | None) -> TradingStatus:
    # 字段语义由上线前能力探针冻结；未知值不得被当作可交易。
    if raw is None:
        return TradingStatus.UNKNOWN
    return {"1": TradingStatus.TRADING, "0": TradingStatus.SUSPENDED}.get(raw, TradingStatus.UNKNOWN)


def _is_st(raw: str | None) -> bool | None:
    if raw == "1":
        return True
    if raw == "0":
        return False
    return None


class BaoStockStatusEnrichmentService:
    def __init__(
        self,
        adapter: BaoStockTradingStatusAdapter,
        artifact_writer: ImmutableArtifactWriter,
        lineage: StatusLineageWriter,
        artifact_uri_prefix: str,
    ) -> None:
        self.adapter = adapter
        self.artifact_writer = artifact_writer
        self.lineage = lineage
        self.artifact_uri_prefix = artifact_uri_prefix.rstrip("/")

    def enrich(
        self,
        *,
        parent_version_id: str,
        parent_artifact: RawArtifact,
        gaps: Iterable[CloseGap],
        policy_version: str,
        policy_document_uri: str,
        mode: StatusEnrichmentMode = StatusEnrichmentMode.EXACT,
        fast_mode_approval_ref: str | None = None,
        fast_mode_operator: str | None = None,
    ) -> StatusEnrichmentResult:
        # 局部导入只请求真实空洞的状态；调用方另行提供正常交易日探针样本。
        gap_items = tuple(gaps)
        if mode is StatusEnrichmentMode.FAST and (not fast_mode_approval_ref or not fast_mode_operator):
            raise ValueError("fast mode requires approval reference and operator")
        self.lineage.ensure_securities(gap.security_id for gap in gap_items)
        self.lineage.ensure_policy(
            SourcePolicy(
                policy_version=policy_version,
                primary_source="baostock" if mode is StatusEnrichmentMode.EXACT else "business_assumption",
                policy_document_uri=policy_document_uri,
            )
        )
        if mode is StatusEnrichmentMode.FAST:
            return self._assume_suspended(
                parent_version_id=parent_version_id,
                parent_artifact=parent_artifact,
                gaps=gap_items,
                policy_version=policy_version,
                approval_ref=fast_mode_approval_ref,
                operator=fast_mode_operator,
            )
        requests = requests_for_days(
            (gap.security_id, gap.trading_day) for gap in gap_items if gap.security_id.exchange is not Exchange.BSE
        )
        batches = self.adapter.fetch(requests)
        facts: list[TradingStatusFact] = []
        for batch in batches:
            content = batch.canonical_bytes()
            artifact_hash = sha256(content).hexdigest()
            key = f"raw/baostock/trading-status/{policy_version}/{artifact_hash}.json"
            self.artifact_writer.put_immutable(key, content)
            artifact = RawArtifact(
                source="baostock",
                source_record_id=batch.query_id,
                source_version="trading-status-v1",
                raw_artifact_uri=f"{self.artifact_uri_prefix}/{key}",
                raw_artifact_hash=artifact_hash,
                license_ref="baostock-public-data",
                source_policy_version=policy_version,
                ingested_at=batch.observed_at,
            )
            self.lineage.save_raw_artifact(artifact)
            for row in batch.rows:
                try:
                    security_id = security_id_from_baostock(row.code)
                except ValueError:
                    continue
                provenance = FieldProvenance(
                    field_name="trading_status",
                    source="baostock",
                    source_record_id=f"{batch.query_id}:{row.code}:{row.date.isoformat()}",
                    raw_artifact_hash=artifact_hash,
                    source_version=artifact.source_version,
                    source_policy_version=policy_version,
                    role=ProvenanceRole.SUPPLEMENT,
                )
                fact = TradingStatusFact(
                    security_id=security_id,
                    trading_day=row.date,
                    trading_status=_status(row.tradestatus),
                    is_st=_is_st(row.is_st),
                    raw_tradestatus=row.tradestatus,
                    raw_is_st=row.is_st,
                    observed_at=batch.observed_at,
                    available_at=batch.observed_at,
                    artifact=artifact,
                    field_provenance=(provenance,),
                )
                self.lineage.save_trading_status_fact(fact)
                facts.append(fact)

        facts_by_key = {(fact.security_id, fact.trading_day): fact for fact in facts}
        reconciliations = [self._reconcile_gap(gap, parent_artifact, facts_by_key.get((gap.security_id, gap.trading_day))) for gap in gap_items]
        for reconciliation in reconciliations:
            self.lineage.save_close_gap_reconciliation(reconciliation, policy_version)
        report = self._report(parent_version_id, facts, reconciliations)
        return StatusEnrichmentResult(
            facts=tuple(facts),
            reconciliations=tuple(reconciliations),
            report=report,
            quality_status=_quality(report, mode),
        )

    def _assume_suspended(
        self,
        *,
        parent_version_id: str,
        parent_artifact: RawArtifact,
        gaps: tuple[CloseGap, ...],
        policy_version: str,
        approval_ref: str | None,
        operator: str | None,
    ) -> StatusEnrichmentResult:
        if not approval_ref or not operator:
            raise ValueError("fast mode requires approval reference and operator")
        evidence = {
            "schema_version": "fast-suspension-assumption-v1",
            "mode": StatusEnrichmentMode.FAST,
            "parent_version_id": parent_version_id,
            "parent_artifact_hash": parent_artifact.raw_artifact_hash,
            "policy_version": policy_version,
            "approval_ref": approval_ref,
            "operator": operator,
            "gaps": [
                {
                    "security_id": f"{gap.security_id.exchange}:{gap.security_id.symbol}",
                    "trading_day": gap.trading_day.isoformat(),
                }
                for gap in gaps
            ],
        }
        content = json.dumps(evidence, sort_keys=True, separators=(",", ":")).encode()
        artifact_hash = sha256(content).hexdigest()
        key = f"raw/business-assumption/close-gap-suspension/{policy_version}/{artifact_hash}.json"
        self.artifact_writer.put_immutable(key, content)
        artifact = RawArtifact(
            source="business_assumption",
            source_record_id=f"fast-suspension:{artifact_hash}",
            source_version="fast-suspension-assumption-v1",
            raw_artifact_uri=f"{self.artifact_uri_prefix}/{key}",
            raw_artifact_hash=artifact_hash,
            license_ref="internal-approved-policy",
            source_policy_version=policy_version,
            ingested_at=datetime.now(UTC),
        )
        self.lineage.save_raw_artifact(artifact)
        reconciliations: list[CloseGapReconciliation] = []
        for gap in gaps:
            primary = self._primary_provenance(gap, parent_artifact)
            assumption = FieldProvenance(
                field_name="trading_status_assumption",
                source="business_assumption",
                source_record_id=f"{approval_ref}:{operator}:{gap.security_id.exchange}:{gap.security_id.symbol}:{gap.trading_day.isoformat()}",
                raw_artifact_hash=artifact_hash,
                source_version=artifact.source_version,
                source_policy_version=policy_version,
                role=ProvenanceRole.SUPPLEMENT,
            )
            reconciliation = CloseGapReconciliation(
                security_id=gap.security_id,
                trading_day=gap.trading_day,
                status=CloseGapReconciliationStatus.SUSPENSION_ASSUMED,
                reason="manual_business_assumption",
                primary_provenance=primary,
                status_provenance=assumption,
            )
            reconciliations.append(reconciliation)
        bulk_saver = getattr(self.lineage, "save_close_gap_reconciliations", None)
        if bulk_saver is not None:
            bulk_saver(reconciliations, policy_version)
        else:
            for reconciliation in reconciliations:
                self.lineage.save_close_gap_reconciliation(reconciliation, policy_version)
        report = self._report(parent_version_id, [], reconciliations)
        return StatusEnrichmentResult(
            mode=StatusEnrichmentMode.FAST,
            facts=(),
            reconciliations=tuple(reconciliations),
            report=report,
            quality_status=_quality(report, StatusEnrichmentMode.FAST),
        )

    @staticmethod
    def _reconcile_gap(
        gap: CloseGap, parent_artifact: RawArtifact, fact: TradingStatusFact | None
    ) -> CloseGapReconciliation:
        primary = BaoStockStatusEnrichmentService._primary_provenance(gap, parent_artifact)
        if fact is None:
            return CloseGapReconciliation(
                security_id=gap.security_id,
                trading_day=gap.trading_day,
                status=CloseGapReconciliationStatus.STATUS_UNKNOWN,
                reason="baostock_status_not_returned",
                primary_provenance=primary,
            )
        status_provenance = fact.field_provenance[0]
        if fact.trading_status is TradingStatus.SUSPENDED:
            outcome, reason = CloseGapReconciliationStatus.SUSPENSION_CONFIRMED, "baostock_tradestatus_0"
        elif fact.trading_status is TradingStatus.TRADING:
            outcome, reason = CloseGapReconciliationStatus.UNEXPLAINED_MISSING, "baostock_tradestatus_1"
        else:
            outcome, reason = CloseGapReconciliationStatus.STATUS_UNKNOWN, "baostock_status_unknown"
        return CloseGapReconciliation(
            security_id=gap.security_id,
            trading_day=gap.trading_day,
            status=outcome,
            reason=reason,
            primary_provenance=primary,
            status_provenance=status_provenance,
        )

    @staticmethod
    def _primary_provenance(gap: CloseGap, parent_artifact: RawArtifact) -> FieldProvenance:
        return FieldProvenance(
            field_name="close",
            source=parent_artifact.source,
            source_record_id=f"{gap.security_id.exchange}:{gap.security_id.symbol}:{gap.trading_day.isoformat()}",
            raw_artifact_hash=parent_artifact.raw_artifact_hash,
            source_version=parent_artifact.source_version,
            source_policy_version=parent_artifact.source_policy_version,
            role=ProvenanceRole.PRIMARY,
        )

    @staticmethod
    def _report(
        parent_version_id: str,
        facts: list[TradingStatusFact],
        reconciliations: list[CloseGapReconciliation],
    ) -> StatusEnrichmentQualityReport:
        counts = {status: 0 for status in CloseGapReconciliationStatus}
        for item in reconciliations:
            counts[item.status] += 1
        total = len(reconciliations)
        unknown = counts[CloseGapReconciliationStatus.STATUS_UNKNOWN]
        assumed = counts[CloseGapReconciliationStatus.SUSPENSION_ASSUMED]
        return StatusEnrichmentQualityReport(
            parent_version_id=parent_version_id,
            close_gap_count=total,
            suspension_confirmed_count=counts[CloseGapReconciliationStatus.SUSPENSION_CONFIRMED],
            suspension_assumed_count=assumed,
            unexplained_missing_count=counts[CloseGapReconciliationStatus.UNEXPLAINED_MISSING],
            status_unknown_count=unknown,
            quarantined_count=counts[CloseGapReconciliationStatus.QUARANTINED],
            st_count=sum(fact.is_st is True for fact in facts),
            status_coverage=0.0 if not total else (total - unknown - assumed) / total,
        )


def _quality(report: StatusEnrichmentQualityReport, mode: StatusEnrichmentMode) -> QualityStatus:
    if mode is StatusEnrichmentMode.FAST:
        return QualityStatus.WARN
    if report.classified_count != report.close_gap_count:
        return QualityStatus.FAIL
    if report.unexplained_missing_count or report.quarantined_count:
        return QualityStatus.FAIL
    if report.status_unknown_count:
        return QualityStatus.WARN
    return QualityStatus.PASS
