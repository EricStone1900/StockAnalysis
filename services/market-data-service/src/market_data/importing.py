import hashlib
import json
from collections.abc import Awaitable
from datetime import datetime
from typing import Protocol

from pydantic import BaseModel, Field, model_validator

from .baostock_status import security_id_from_qlib
from .domain import Exchange
from .investment_data import ImmutableArtifactWriter, InvestmentDataReleaseAdapter, LandedRelease
from .pit import RawArtifact
from .qlib_quality import (
    QlibDailyQualityReport,
    build_close_gap_index,
    close_gap_index_bytes,
    extract_qlib_close_gaps,
    parse_close_gap_index,
    validate_qlib_daily_archive,
)
from .repository import SourcePolicy
from .status_batches import StatusBatch, plan_status_batches
from .status_enrichment import BaoStockStatusEnrichmentService, CloseGap, StatusEnrichmentResult
from .trading_status import StatusEnrichmentMode
from .universe import is_stage03_cn_a_equity
from .versioning import DataVersion


class SourceLineageWriter(Protocol):
    def ensure_policy(self, policy: SourcePolicy) -> None: ...

    def save_raw_artifact(self, artifact: RawArtifact) -> None: ...

    def save_data_version(self, version: DataVersion) -> None: ...


class DataVersionSink(Protocol):
    def publish(self, candidate: DataVersion, idempotency_key: str) -> Awaitable[DataVersion]: ...


class InvestmentDataImportCommand(BaseModel):
    release_tag: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    policy_version: str = Field(min_length=1)
    policy_document_uri: str = Field(min_length=1)
    available_at: datetime


class BaoStockStatusEnrichmentCommand(BaseModel):
    parent_version: DataVersion
    policy_version: str = Field(min_length=1)
    policy_document_uri: str = Field(min_length=1)
    available_at: datetime
    max_gaps: int | None = Field(default=None, ge=1)
    probe: bool = False
    exclude_bse: bool = True
    exclude_non_equity: bool = True
    batch_size: int | None = Field(default=None, ge=1)
    batch_ordinal: int | None = Field(default=None, ge=0)
    mode: StatusEnrichmentMode = StatusEnrichmentMode.FAST
    fast_mode_acknowledged: bool = False
    fast_mode_approval_ref: str | None = Field(default=None, min_length=1)
    fast_mode_operator: str | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def validate_mode(self) -> "BaoStockStatusEnrichmentCommand":
        if self.mode is StatusEnrichmentMode.FAST:
            if not self.fast_mode_acknowledged:
                raise ValueError("fast mode requires fast_mode_acknowledged=true")
            if not self.fast_mode_approval_ref or not self.fast_mode_operator:
                raise ValueError("fast mode requires approval reference and operator")
            if "fast" not in self.policy_version.lower():
                raise ValueError("fast mode requires a distinct policy_version containing 'fast'")
        return self


class StructuralQualityReport(BaseModel):
    source: str = "investment_data"
    release_tag: str
    archive_hash: str
    manifest_hash: str
    target_trade_date: str
    status: str = "PASS"
    checks: tuple[str, ...] = (
        "manifest_schema",
        "archive_identity",
        "archive_member_safety",
        "calendar_and_instrument_dates",
    )
    daily_quality: QlibDailyQualityReport


class InvestmentDataImportService:
    def __init__(
        self,
        adapter: InvestmentDataReleaseAdapter,
        artifact_writer: ImmutableArtifactWriter,
        lineage: SourceLineageWriter,
        publisher: DataVersionSink,
        artifact_uri_prefix: str,
    ) -> None:
        self.adapter = adapter
        self.artifact_writer = artifact_writer
        self.lineage = lineage
        self.publisher = publisher
        self.artifact_uri_prefix = artifact_uri_prefix.rstrip("/")

    async def import_release(self, command: InvestmentDataImportCommand, idempotency_key: str) -> DataVersion:
        policy = SourcePolicy(
            policy_version=command.policy_version,
            primary_source="investment_data",
            policy_document_uri=command.policy_document_uri,
        )
        self.lineage.ensure_policy(policy)
        validated = self.adapter.download_and_validate(command.release_tag)
        landed = self.adapter.land(
            validated,
            self.artifact_writer,
            command.policy_version,
            self.artifact_uri_prefix,
        )
        self.lineage.save_raw_artifact(landed.archive_artifact)
        self.lineage.save_raw_artifact(landed.manifest_artifact)
        daily_quality = validate_qlib_daily_archive(landed.validated.archive)
        gap_index = build_close_gap_index(landed.validated.archive, landed.validated.archive_hash)
        index_key = f"quality/investment_data/{landed.validated.manifest.release_tag}/{landed.validated.archive_hash}/close-gap-index.json"
        index_hash = self.artifact_writer.put_immutable(index_key, close_gap_index_bytes(gap_index))
        index_uri = f"{self.artifact_uri_prefix}/{index_key}"
        quality_report_uri = self._write_quality_report(landed, daily_quality)
        candidate = landed.build_data_version(
            command.policy_version,
            command.available_at,
            quality_report_uri=quality_report_uri,
            close_gap_index_uri=index_uri,
            close_gap_index_hash=index_hash,
        )
        candidate = candidate.model_copy(update={"quality_status": daily_quality.status})
        published = await self.publisher.publish(candidate, idempotency_key)
        self._persist_version(published)
        return published

    def _persist_version(self, version: DataVersion) -> None:
        saver = getattr(self.lineage, "save_data_version", None)
        if saver is not None:
            saver(version)

    def _write_quality_report(self, landed: LandedRelease, daily_quality: QlibDailyQualityReport) -> str:
        report = StructuralQualityReport(
            release_tag=landed.validated.manifest.release_tag,
            archive_hash=landed.validated.archive_hash,
            manifest_hash=landed.validated.manifest_hash,
            target_trade_date=landed.validated.manifest.target_trade_date.isoformat(),
            status=daily_quality.status,
            daily_quality=daily_quality,
        )
        content = json.dumps(report.model_dump(mode="json"), sort_keys=True, separators=(",", ":")).encode()
        key = (
            f"quality/investment_data/{report.release_tag}/{report.archive_hash}/"
            "structural-quality-report.json"
        )
        self.artifact_writer.put_immutable(key, content)
        return f"{self.artifact_uri_prefix}/{key}"


class ArchiveReader(Protocol):
    def get_verified(self, key: str, expected_hash: str) -> bytes: ...


class StatusBatchProgress(Protocol):
    def ensure_batches(self, parent_version_id: str, policy_version: str, batches: tuple[StatusBatch, ...]) -> None: ...

    def claim(self, batch_id: str) -> bool: ...

    def mark_succeeded(self, batch_id: str) -> None: ...

    def mark_failed(self, batch_id: str, error: str) -> None: ...


class BaoStockStatusImportService:
    """由已固化的父Qlib归档产生状态增强版本，禁止重新下载主数据。"""

    def __init__(
        self,
        reader: ArchiveReader,
        writer: ImmutableArtifactWriter,
        enrichment: BaoStockStatusEnrichmentService,
        publisher: DataVersionSink,
        artifact_uri_prefix: str,
        batch_progress: StatusBatchProgress | None = None,
    ) -> None:
        self.reader = reader
        self.writer = writer
        self.enrichment = enrichment
        self.publisher = publisher
        self.artifact_uri_prefix = artifact_uri_prefix.rstrip("/")
        self.batch_progress = batch_progress

    async def import_status(
        self, command: BaoStockStatusEnrichmentCommand, idempotency_key: str
    ) -> DataVersion | StatusEnrichmentResult:
        parent = command.parent_version
        prefix = f"{self.artifact_uri_prefix}/"
        if not parent.artifact_uri.startswith(prefix):
            raise ValueError("parent artifact URI does not belong to configured bucket")
        archive: bytes | None = None
        parent_artifact = RawArtifact(
            source="investment_data",
            source_record_id=f"{parent.source_release_tag or parent.version_id}/qlib_bin.tar.gz",
            source_version=parent.source_version,
            source_release_tag=parent.source_release_tag,
            raw_artifact_uri=parent.artifact_uri,
            raw_artifact_hash=parent.artifact_hash,
            license_ref="https://github.com/chenditc/investment_data/blob/main/LICENSE",
            source_policy_version=parent.source_policy_version,
            ingested_at=parent.available_at,
        )
        if parent.close_gap_index_uri and parent.close_gap_index_hash:
            index_key = parent.close_gap_index_uri.removeprefix(prefix)
            index_content = self.reader.get_verified(index_key, parent.close_gap_index_hash)
            indexed_gaps = parse_close_gap_index(index_content, parent.artifact_hash).gaps
        else:
            archive = self.reader.get_verified(parent.artifact_uri.removeprefix(prefix), parent.artifact_hash)
            indexed_gaps = extract_qlib_close_gaps(archive)
        all_gaps = tuple(CloseGap(security_id=security_id_from_qlib(gap.symbol), trading_day=gap.trading_day) for gap in indexed_gaps)
        excluded_bse_gap_count = sum(gap.security_id.exchange is Exchange.BSE for gap in all_gaps) if command.exclude_bse else 0
        gaps_after_bse = tuple(gap for gap in all_gaps if gap.security_id.exchange is not Exchange.BSE) if command.exclude_bse else all_gaps
        excluded_non_equity_gap_count = sum(not is_stage03_cn_a_equity(gap.security_id) for gap in gaps_after_bse) if command.exclude_non_equity else 0
        eligible_gaps = tuple(gap for gap in gaps_after_bse if is_stage03_cn_a_equity(gap.security_id)) if command.exclude_non_equity else gaps_after_bse
        selected_batch: StatusBatch | None = None
        if (command.batch_size is None) != (command.batch_ordinal is None):
            raise ValueError("batch_size and batch_ordinal must be provided together")
        if command.batch_size is not None and command.batch_ordinal is not None:
            if not command.probe:
                raise ValueError("partial batch execution requires probe mode")
            if self.batch_progress is None:
                raise ValueError("status batch progress repository is required")
            lineage = getattr(self.enrichment, "lineage", None)
            if lineage is not None:
                lineage.ensure_policy(
                    SourcePolicy(
                        policy_version=command.policy_version,
                        primary_source="baostock" if command.mode is StatusEnrichmentMode.EXACT else "business_assumption",
                        policy_document_uri=command.policy_document_uri,
                    )
                )
            identity_namespace = (
                f"{parent.version_id}:{command.policy_version}"
                if command.mode is StatusEnrichmentMode.FAST
                else ""
            )
            batches = plan_status_batches(
                eligible_gaps,
                command.batch_size,
                identity_namespace=identity_namespace,
            )
            if command.batch_ordinal >= len(batches):
                raise ValueError("batch_ordinal is outside the planned range")
            selected_batch = batches[command.batch_ordinal]
            # 受控探针只执行一个批次；全量批次计划可能包含数十万条记录，
            # 逐条预注册会让探针本身变成不可接受的长事务。正式导入再由
            # 调度器按批次逐步登记和领取。
            self.batch_progress.ensure_batches(parent.version_id, command.policy_version, (selected_batch,))
            if not self.batch_progress.claim(selected_batch.batch_id):
                raise ValueError("status batch is not claimable")
            start = selected_batch.ordinal * command.batch_size
            gaps = eligible_gaps[start : start + command.batch_size]
        else:
            gaps = eligible_gaps[: command.max_gaps] if command.max_gaps is not None else eligible_gaps
        if command.probe and command.max_gaps is None and selected_batch is None:
            raise ValueError("probe requires max_gaps")
        try:
            result = self.enrichment.enrich(
                parent_version_id=parent.version_id,
                parent_artifact=parent_artifact,
                gaps=gaps,
                policy_version=command.policy_version,
                policy_document_uri=command.policy_document_uri,
                mode=command.mode,
                fast_mode_approval_ref=command.fast_mode_approval_ref,
                fast_mode_operator=command.fast_mode_operator,
            )
        except Exception as error:
            if selected_batch is not None:
                if self.batch_progress is None:
                    raise AssertionError("claimed batch requires progress repository")
                self.batch_progress.mark_failed(selected_batch.batch_id, str(error))
            raise
        result = result.model_copy(
            update={"report": result.report.model_copy(update={"excluded_bse_gap_count": excluded_bse_gap_count, "excluded_non_equity_gap_count": excluded_non_equity_gap_count})}
        )
        if any(fact.available_at > command.available_at for fact in result.facts):
            if selected_batch is not None:
                if self.batch_progress is None:
                    raise AssertionError("claimed batch requires progress repository")
                self.batch_progress.mark_failed(selected_batch.batch_id, "available_at precedes captured evidence")
            raise ValueError("status enhanced version available_at must not precede captured evidence")
        if selected_batch is not None:
            if self.batch_progress is None:
                raise AssertionError("claimed batch requires progress repository")
            self.batch_progress.mark_succeeded(selected_batch.batch_id)
        if command.probe:
            return result
        payload = json.dumps(
            {"report": result.report.model_dump(mode="json"), "quality_status": result.quality_status},
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
        report_hash = self.writer.put_immutable(f"quality/baostock-status/{parent.version_id}/{hashlib.sha256(payload).hexdigest()}.json", payload)
        candidate = parent.model_copy(
            update={
                "version_id": f"{parent.version_id}-baostock-status-{report_hash[:12]}",
                "scope": "CN_A_EQUITY_EX_BSE" if command.exclude_bse and command.exclude_non_equity else parent.scope,
                "source_version": "baostock-trading-status-v1",
                "source_policy_version": command.policy_version,
                "quality_report_uri": f"{self.artifact_uri_prefix}/quality/baostock-status/{parent.version_id}/{report_hash}.json",
                "quality_status": result.quality_status,
                "available_at": command.available_at,
                "content_hash": report_hash,
                "parent_version_id": parent.version_id,
            }
        )
        published = await self.publisher.publish(candidate, idempotency_key)
        saver = getattr(self.enrichment.lineage, "save_data_version", None)
        if saver is not None:
            saver(published)
        return published
