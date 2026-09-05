import asyncio
import hashlib
import io
import json
import struct
import tarfile
from datetime import UTC, datetime

import pytest

from market_data.baostock_status import BaoStockTradingStatusAdapter
from market_data.importing import (
    BaoStockStatusEnrichmentCommand,
    BaoStockStatusImportService,
    InvestmentDataImportCommand,
    InvestmentDataImportService,
)
from market_data.investment_data import (
    ARCHIVE_NAME,
    MANIFEST_NAME,
    REQUIRED_ARCHIVE_MEMBERS,
    InvestmentDataReleaseAdapter,
)
from market_data.pit import RawArtifact
from market_data.qlib_quality import build_close_gap_index, close_gap_index_bytes
from market_data.repository import SourcePolicy
from market_data.status_enrichment import BaoStockStatusEnrichmentService
from market_data.versioning import DataVersion, DataVersionStatus


class FakeFetcher:
    def __init__(self, assets: dict[str, bytes]) -> None:
        self.assets = assets

    def fetch(self, url: str) -> bytes:
        return self.assets[url]


class InMemoryWriter:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    def put_immutable(self, key: str, content: bytes) -> str:
        existing = self.objects.setdefault(key, content)
        if existing != content:
            raise ValueError("immutable object conflict")
        return hashlib.sha256(content).hexdigest()

    def get_verified(self, key: str, expected_hash: str) -> bytes:
        content = self.objects[key]
        if hashlib.sha256(content).hexdigest() != expected_hash:
            raise ValueError("hash mismatch")
        return content


class InMemoryLineage:
    def __init__(self) -> None:
        self.policies: dict[str, SourcePolicy] = {}
        self.artifacts: dict[str, RawArtifact] = {}

    def ensure_policy(self, policy: SourcePolicy) -> None:
        existing = self.policies.setdefault(policy.policy_version, policy)
        if existing != policy:
            raise ValueError("source policy version is immutable")

    def ensure_securities(self, security_ids: object) -> None:
        pass

    def save_raw_artifact(self, artifact: RawArtifact) -> None:
        self.artifacts[artifact.raw_artifact_hash] = artifact

    def save_trading_status_fact(self, fact: object) -> None:
        pass

    def save_close_gap_reconciliation(self, reconciliation: object, policy_version: str) -> None:
        pass


class InMemoryPublisher:
    async def publish(self, candidate: DataVersion, _: str) -> DataVersion:
        return candidate.model_copy(update={"status": DataVersionStatus.READY})


class InMemoryBatchProgress:
    def __init__(self) -> None:
        self.batches: dict[str, str] = {}
        self.claimed: list[str] = []
        self.succeeded: list[str] = []
        self.failed: list[tuple[str, str]] = []

    def ensure_batches(self, parent_version_id: str, policy_version: str, batches: tuple[object, ...]) -> None:
        for batch in batches:
            self.batches.setdefault(batch.batch_id, "PENDING")  # type: ignore[attr-defined]

    def claim(self, batch_id: str) -> bool:
        if self.batches.get(batch_id) not in {"PENDING", "FAILED"}:
            return False
        self.batches[batch_id] = "RUNNING"
        self.claimed.append(batch_id)
        return True

    def mark_succeeded(self, batch_id: str) -> None:
        assert self.batches[batch_id] == "RUNNING"
        self.batches[batch_id] = "SUCCEEDED"
        self.succeeded.append(batch_id)

    def mark_failed(self, batch_id: str, error: str) -> None:
        self.batches[batch_id] = "FAILED"
        self.failed.append((batch_id, error))


class FailingEnrichment:
    def enrich(self, **_: object) -> object:
        raise RuntimeError("supplier timeout")


def archive(*, close_gap: bool = False) -> bytes:
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode="w:gz") as target:
        files = {
            "qlib_bin/calendars/day.txt": b"2026-08-28\n",
            "qlib_bin/calendars/day_future.txt": b"2026-08-28\n2026-08-31\n",
        }
        files.update({name: b"sh600000\t2020-01-01\t2026-08-28\n" for name in REQUIRED_ARCHIVE_MEMBERS[2:]})
        for field, values in {
            "open": (10.0,),
            "high": (11.0,),
            "low": (9.0,),
            "close": (float("nan") if close_gap else 10.5,),
            "volume": (100.0,),
        }.items():
            files[f"qlib_bin/features/sh600000/{field}.day.bin"] = struct.pack("<2f", 0.0, *values)
        for name, content in files.items():
            entry = tarfile.TarInfo(name)
            entry.size = len(content)
            target.addfile(entry, io.BytesIO(content))
    return stream.getvalue()


def manifest(archive_bytes: bytes) -> bytes:
    return json.dumps(
        {
            "release_tag": "2026-08-28",
            "target_trade_date": "2026-08-28",
            "future_start_date": "2026-08-31",
            "future_end_date": "2026-08-31",
            "dolt_commit": "a" * 32,
            "investment_data_commit": "b" * 40,
            "qlib_commit": "c" * 40,
            "image_digest": f"sha256:{'d' * 64}",
            "archive_size_bytes": len(archive_bytes),
            "archive_sha256": f"sha256:{hashlib.sha256(archive_bytes).hexdigest()}",
        },
        separators=(",", ":"),
    ).encode()


def test_import_persists_lineage_writes_quality_report_and_publishes_version() -> None:
    archive_bytes = archive()
    root = "https://example.test/releases"
    adapter = InvestmentDataReleaseAdapter(
        FakeFetcher(
            {
                f"{root}/2026-08-28/{MANIFEST_NAME}": manifest(archive_bytes),
                f"{root}/2026-08-28/{ARCHIVE_NAME}": archive_bytes,
            }
        ),
        root,
    )
    writer = InMemoryWriter()
    lineage = InMemoryLineage()
    service = InvestmentDataImportService(adapter, writer, lineage, InMemoryPublisher(), "minio://test-artifacts")

    version = asyncio.run(
        service.import_release(
            InvestmentDataImportCommand(
                release_tag="2026-08-28",
                policy_version="v1",
                policy_document_uri="docs://source-policy/v1",
                available_at=datetime(2026, 8, 29, tzinfo=UTC),
            ),
            "import-2026-08-28",
        )
    )

    assert version.status is DataVersionStatus.READY
    assert version.quality_report_uri is not None
    report_key = version.quality_report_uri.removeprefix("minio://test-artifacts/")
    assert json.loads(writer.objects[report_key])["daily_quality"]["status"] == "PASS"
    assert len(lineage.artifacts) == 2
    assert lineage.policies["v1"].primary_source == "investment_data"
    repeated = asyncio.run(
        service.import_release(
            InvestmentDataImportCommand(
                release_tag="2026-08-28",
                policy_version="v1",
                policy_document_uri="docs://source-policy/v1",
                available_at=datetime(2026, 8, 29, tzinfo=UTC),
            ),
            "import-2026-08-28",
        )
    )
    assert repeated == version
    assert len(lineage.artifacts) == 2


class RecordedBaoStockClient:
    def login(self) -> None:
        pass

    def query_history(self, code: str, start: object, end: object) -> list[dict[str, str]]:
        return [{"date": "2026-08-28", "code": code, "tradestatus": "0", "isST": "1"}]

    def logout(self) -> None:
        pass


def test_status_import_reads_parent_archive_writes_report_and_publishes_enhanced_version() -> None:
    archive_bytes = archive(close_gap=True)
    writer = InMemoryWriter()
    archive_hash = writer.put_immutable("raw/parent.tar.gz", archive_bytes)
    parent = DataVersion(
        version_id="parent-v1",
        scope="CN_A",
        source_version="b" * 40,
        source_release_tag="2026-08-28",
        source_policy_version="v1",
        artifact_uri="minio://test-artifacts/raw/parent.tar.gz",
        artifact_hash=archive_hash,
        quality_status="WARN",
        available_at=datetime(2026, 8, 29, tzinfo=UTC),
        content_hash=archive_hash,
    )
    observed_at = datetime(2026, 8, 30, tzinfo=UTC)
    lineage = InMemoryLineage()
    enrichment = BaoStockStatusEnrichmentService(
        BaoStockTradingStatusAdapter(RecordedBaoStockClient, now=lambda: observed_at),
        writer,
        lineage,
        "minio://test-artifacts",
    )
    service = BaoStockStatusImportService(writer, writer, enrichment, InMemoryPublisher(), "minio://test-artifacts")

    version = asyncio.run(
        service.import_status(
            BaoStockStatusEnrichmentCommand(
                parent_version=parent,
                policy_version="v1-baostock-status",
                policy_document_uri="docs/status.md",
                available_at=observed_at,
                mode="exact",
            ),
            "enrich-parent-v1",
        )
    )

    assert version.status is DataVersionStatus.READY
    assert version.parent_version_id == "parent-v1"
    assert version.quality_status == "PASS"
    assert version.quality_report_uri is not None
    report_key = version.quality_report_uri.removeprefix("minio://test-artifacts/")
    report = json.loads(writer.objects[report_key])
    assert report["report"]["close_gap_count"] == 1
    assert report["report"]["suspension_confirmed_count"] == 1


def test_status_probe_requires_limit_and_does_not_publish_version() -> None:
    archive_bytes = archive(close_gap=True)
    writer = InMemoryWriter()
    archive_hash = writer.put_immutable("raw/parent.tar.gz", archive_bytes)
    parent = DataVersion(version_id="parent-v1", scope="CN_A", source_version="b" * 40, artifact_uri="minio://test-artifacts/raw/parent.tar.gz", artifact_hash=archive_hash, quality_status="WARN", available_at=datetime(2026, 8, 29, tzinfo=UTC), content_hash=archive_hash)
    enrichment = BaoStockStatusEnrichmentService(BaoStockTradingStatusAdapter(RecordedBaoStockClient, now=lambda: datetime(2026, 8, 30, tzinfo=UTC)), writer, InMemoryLineage(), "minio://test-artifacts")
    service = BaoStockStatusImportService(writer, writer, enrichment, InMemoryPublisher(), "minio://test-artifacts")
    command = BaoStockStatusEnrichmentCommand(parent_version=parent, policy_version="v1-baostock-status", policy_document_uri="docs/status.md", available_at=datetime(2026, 8, 30, tzinfo=UTC), max_gaps=1, probe=True, mode="exact")

    result = asyncio.run(service.import_status(command, "probe-parent-v1"))
    assert result.report.close_gap_count == 1


def test_fast_mode_requires_explicit_acknowledgement_and_a_distinct_policy_version() -> None:
    parent = DataVersion(
        version_id="parent-fast-v1",
        scope="CN_A",
        source_version="b" * 40,
        artifact_uri="minio://test-artifacts/raw/parent.tar.gz",
        artifact_hash="a" * 64,
        quality_status="WARN",
        available_at=datetime(2026, 8, 29, tzinfo=UTC),
        content_hash="a" * 64,
    )
    with pytest.raises(ValueError, match="acknowledged"):
        BaoStockStatusEnrichmentCommand(
            parent_version=parent,
            policy_version="v1-close-gap-fast",
            policy_document_uri="docs/status-fast.md",
            available_at=datetime(2026, 8, 30, tzinfo=UTC),
            max_gaps=1,
            probe=True,
            fast_mode_approval_ref="risk-waiver-2026-08-30",
            fast_mode_operator="eric",
        )
    with pytest.raises(ValueError, match="containing 'fast'"):
        BaoStockStatusEnrichmentCommand(
            parent_version=parent,
            policy_version="v1-close-gap",
            policy_document_uri="docs/status-fast.md",
            available_at=datetime(2026, 8, 30, tzinfo=UTC),
            max_gaps=1,
            probe=True,
            mode="fast",
            fast_mode_acknowledged=True,
            fast_mode_approval_ref="risk-waiver-2026-08-30",
            fast_mode_operator="eric",
        )


def test_status_batch_probe_claims_and_completes_only_selected_batch() -> None:
    archive_bytes = archive(close_gap=True)
    writer = InMemoryWriter()
    archive_hash = writer.put_immutable("raw/parent.tar.gz", archive_bytes)
    index = build_close_gap_index(archive_bytes, archive_hash)
    index_hash = writer.put_immutable("quality/index.json", close_gap_index_bytes(index))
    parent = DataVersion(version_id="parent-batch-v1", scope="CN_A", source_version="b" * 40, artifact_uri="minio://test-artifacts/raw/parent.tar.gz", artifact_hash=archive_hash, close_gap_index_uri="minio://test-artifacts/quality/index.json", close_gap_index_hash=index_hash, quality_status="WARN", available_at=datetime(2026, 8, 29, tzinfo=UTC), content_hash=archive_hash)
    progress = InMemoryBatchProgress()
    enrichment = BaoStockStatusEnrichmentService(BaoStockTradingStatusAdapter(RecordedBaoStockClient, now=lambda: datetime(2026, 8, 30, tzinfo=UTC)), writer, InMemoryLineage(), "minio://test-artifacts")
    service = BaoStockStatusImportService(writer, writer, enrichment, InMemoryPublisher(), "minio://test-artifacts", progress)

    result = asyncio.run(
        service.import_status(
            BaoStockStatusEnrichmentCommand(parent_version=parent, policy_version="v1-baostock-status", policy_document_uri="docs/status.md", available_at=datetime(2026, 8, 30, tzinfo=UTC), probe=True, batch_size=1, batch_ordinal=0, mode="exact"),
            "batch-probe-001",
        )
    )

    assert result.report.close_gap_count == 1
    assert len(progress.claimed) == 1
    assert progress.succeeded == progress.claimed


def test_fast_status_batch_registers_its_distinct_policy_before_claiming() -> None:
    archive_bytes = archive(close_gap=True)
    writer = InMemoryWriter()
    archive_hash = writer.put_immutable("raw/parent.tar.gz", archive_bytes)
    index = build_close_gap_index(archive_bytes, archive_hash)
    index_hash = writer.put_immutable("quality/index.json", close_gap_index_bytes(index))
    parent = DataVersion(version_id="parent-fast-batch-v1", scope="CN_A", source_version="b" * 40, artifact_uri="minio://test-artifacts/raw/parent.tar.gz", artifact_hash=archive_hash, close_gap_index_uri="minio://test-artifacts/quality/index.json", close_gap_index_hash=index_hash, quality_status="WARN", available_at=datetime(2026, 8, 29, tzinfo=UTC), content_hash=archive_hash)
    progress = InMemoryBatchProgress()
    lineage = InMemoryLineage()
    enrichment = BaoStockStatusEnrichmentService(BaoStockTradingStatusAdapter(RecordedBaoStockClient), writer, lineage, "minio://test-artifacts")
    service = BaoStockStatusImportService(writer, writer, enrichment, InMemoryPublisher(), "minio://test-artifacts", progress)

    result = asyncio.run(
        service.import_status(
            BaoStockStatusEnrichmentCommand(parent_version=parent, policy_version="v1-close-gap-fast", policy_document_uri="docs/status-fast.md", available_at=datetime(2026, 8, 30, tzinfo=UTC), probe=True, batch_size=1, batch_ordinal=0, fast_mode_acknowledged=True, fast_mode_approval_ref="risk-waiver-2026-08-30", fast_mode_operator="eric"),
            "fast-batch-probe-001",
        )
    )

    assert result.mode.value == "fast"
    assert lineage.policies["v1-close-gap-fast"].primary_source == "business_assumption"
    assert progress.succeeded == progress.claimed


def test_status_batch_probe_marks_claimed_batch_failed_when_enrichment_fails() -> None:
    archive_bytes = archive(close_gap=True)
    writer = InMemoryWriter()
    archive_hash = writer.put_immutable("raw/parent.tar.gz", archive_bytes)
    parent = DataVersion(version_id="parent-batch-failure-v1", scope="CN_A", source_version="b" * 40, artifact_uri="minio://test-artifacts/raw/parent.tar.gz", artifact_hash=archive_hash, quality_status="WARN", available_at=datetime(2026, 8, 29, tzinfo=UTC), content_hash=archive_hash)
    progress = InMemoryBatchProgress()
    service = BaoStockStatusImportService(writer, writer, FailingEnrichment(), InMemoryPublisher(), "minio://test-artifacts", progress)  # type: ignore[arg-type]

    with pytest.raises(RuntimeError, match="supplier timeout"):
        asyncio.run(
            service.import_status(
                BaoStockStatusEnrichmentCommand(parent_version=parent, policy_version="v1-baostock-status", policy_document_uri="docs/status.md", available_at=datetime(2026, 8, 30, tzinfo=UTC), probe=True, batch_size=1, batch_ordinal=0, mode="exact"),
                "batch-probe-failure-001",
            )
        )

    assert len(progress.claimed) == 1
    assert progress.failed == [(progress.claimed[0], "supplier timeout")]
    assert progress.batches[progress.claimed[0]] == "FAILED"
