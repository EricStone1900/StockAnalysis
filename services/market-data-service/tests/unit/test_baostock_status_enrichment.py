import socket
from datetime import UTC, date, datetime

import pytest

from market_data.baostock_status import (
    BaoStockTradingStatusAdapter,
    RetryPolicy,
    baostock_code,
    security_id_from_baostock,
)
from market_data.domain import Exchange, SecurityId
from market_data.pit import RawArtifact
from market_data.quality import QualityStatus
from market_data.status_enrichment import BaoStockStatusEnrichmentService, CloseGap
from market_data.trading_status import (
    CloseGapReconciliationStatus,
    StatusEnrichmentMode,
    visible_trading_status,
)


class FakeBaoStockClient:
    def __init__(self, rows: list[dict[str, str]]) -> None:
        self.rows = rows
        self.logged_in = False
        self.logged_out = False

    def login(self) -> None:
        self.logged_in = True

    def query_history(self, code: str, start: date, end: date) -> list[dict[str, str]]:
        return [row for row in self.rows if row["code"] == code]

    def logout(self) -> None:
        self.logged_out = True


class FakeArtifactWriter:
    def __init__(self) -> None:
        self.items: dict[str, bytes] = {}

    def put_immutable(self, key: str, content: bytes) -> str:
        self.items.setdefault(key, content)
        return "unused"


class FakeLineage:
    def __init__(self) -> None:
        self.policies: list[object] = []
        self.artifacts: list[RawArtifact] = []
        self.facts: list[object] = []
        self.reconciliations: list[object] = []

    def ensure_policy(self, policy: object) -> None:
        self.policies.append(policy)

    def ensure_securities(self, security_ids: object) -> None:
        self.security_ids = tuple(security_ids)  # type: ignore[arg-type]

    def save_raw_artifact(self, artifact: RawArtifact) -> None:
        self.artifacts.append(artifact)

    def save_trading_status_fact(self, fact: object) -> None:
        self.facts.append(fact)

    def save_close_gap_reconciliation(self, reconciliation: object, policy_version: str) -> None:
        self.reconciliations.append((reconciliation, policy_version))


def parent_artifact() -> RawArtifact:
    return RawArtifact(
        source="investment_data",
        source_record_id="2026-08-29",
        source_version="763d89573f21b04259652818b25930e32319ee33",
        source_release_tag="2026-08-29",
        raw_artifact_uri="minio://artifacts/raw/investment_data/archive.tar.gz",
        raw_artifact_hash="a" * 64,
        license_ref="investment_data-license",
        source_policy_version="v1",
        ingested_at=datetime(2026, 8, 31, tzinfo=UTC),
    )


def test_baostock_code_mapping_covers_cn_exchanges() -> None:
    assert baostock_code(SecurityId(exchange=Exchange.SSE, symbol="600000")) == "sh.600000"
    assert baostock_code(SecurityId(exchange=Exchange.SZSE, symbol="000001")) == "sz.000001"
    assert security_id_from_baostock("bj.430047") == SecurityId(exchange=Exchange.BSE, symbol="430047")
    with pytest.raises(ValueError, match="does not support"):
        baostock_code(SecurityId(exchange=Exchange.BSE, symbol="430047"))


def test_status_enrichment_keeps_gap_and_classifies_it_from_immutable_evidence() -> None:
    observed_at = datetime(2026, 8, 29, 12, tzinfo=UTC)
    client = FakeBaoStockClient(
        [
            {"date": "2026-08-28", "code": "sh.600000", "tradestatus": "0", "isST": "1"},
            {"date": "2026-08-28", "code": "sz.000001", "tradestatus": "1", "isST": "0"},
        ]
    )
    adapter = BaoStockTradingStatusAdapter(lambda: client, now=lambda: observed_at)
    lineage = FakeLineage()
    result = BaoStockStatusEnrichmentService(adapter, FakeArtifactWriter(), lineage, "minio://artifacts").enrich(
        parent_version_id="cn-a-investment-data-2026-08-29-aeecdc530b93",
        parent_artifact=parent_artifact(),
        gaps=(
            CloseGap(security_id=SecurityId(exchange=Exchange.SSE, symbol="600000"), trading_day=date(2026, 8, 28)),
            CloseGap(security_id=SecurityId(exchange=Exchange.SZSE, symbol="000001"), trading_day=date(2026, 8, 28)),
        ),
        policy_version="v1-baostock-status",
        policy_document_uri="docs/development-roadmap-v2/02-market-data-service/07-baostock-status-st-enrichment.md",
    )

    assert client.logged_in and client.logged_out
    assert result.report.close_gap_count == 2
    assert result.report.suspension_confirmed_count == 1
    assert result.report.unexplained_missing_count == 1
    assert result.report.st_count == 1
    assert result.quality_status is QualityStatus.FAIL
    assert result.reconciliations[0].status is CloseGapReconciliationStatus.SUSPENSION_CONFIRMED
    assert result.reconciliations[1].status is CloseGapReconciliationStatus.UNEXPLAINED_MISSING
    assert result.facts[0].available_at == observed_at
    assert lineage.artifacts and lineage.facts and lineage.reconciliations
    assert len(lineage.security_ids) == 2


def test_unreturned_status_remains_warn_instead_of_being_assumed_suspended() -> None:
    adapter = BaoStockTradingStatusAdapter(lambda: FakeBaoStockClient([]), now=lambda: datetime(2026, 8, 29, tzinfo=UTC))
    result = BaoStockStatusEnrichmentService(adapter, FakeArtifactWriter(), FakeLineage(), "minio://artifacts").enrich(
        parent_version_id="parent-v1",
        parent_artifact=parent_artifact(),
        gaps=(CloseGap(security_id=SecurityId(exchange=Exchange.SSE, symbol="600000"), trading_day=date(2026, 8, 28)),),
        policy_version="v1-baostock-status",
        policy_document_uri="docs/status.md",
    )

    assert result.report.status_unknown_count == 1
    assert result.quality_status is QualityStatus.WARN
    assert result.reconciliations[0].status is CloseGapReconciliationStatus.STATUS_UNKNOWN


def test_fast_mode_records_auditable_assumption_without_calling_baostock() -> None:
    client = FakeBaoStockClient([])
    lineage = FakeLineage()
    result = BaoStockStatusEnrichmentService(
        BaoStockTradingStatusAdapter(lambda: client), FakeArtifactWriter(), lineage, "minio://artifacts"
    ).enrich(
        parent_version_id="parent-v1",
        parent_artifact=parent_artifact(),
        gaps=(CloseGap(security_id=SecurityId(exchange=Exchange.SSE, symbol="600000"), trading_day=date(2026, 8, 28)),),
        policy_version="v1-close-gap-fast",
        policy_document_uri="docs/status-fast.md",
        mode=StatusEnrichmentMode.FAST,
        fast_mode_approval_ref="risk-waiver-2026-08-30",
        fast_mode_operator="eric",
    )

    assert not client.logged_in
    assert result.mode is StatusEnrichmentMode.FAST
    assert result.facts == ()
    assert result.report.suspension_assumed_count == 1
    assert result.report.status_coverage == 0
    assert result.quality_status is QualityStatus.WARN
    assert result.reconciliations[0].status is CloseGapReconciliationStatus.SUSPENSION_ASSUMED
    assert result.reconciliations[0].reason == "manual_business_assumption"
    assert result.reconciliations[0].status_provenance is not None
    assert result.reconciliations[0].status_provenance.source == "business_assumption"
    assert lineage.artifacts[0].source == "business_assumption"


def test_bse_gap_is_retained_as_unknown_without_calling_baostock() -> None:
    client = FakeBaoStockClient([])
    result = BaoStockStatusEnrichmentService(
        BaoStockTradingStatusAdapter(lambda: client), FakeArtifactWriter(), FakeLineage(), "minio://artifacts"
    ).enrich(
        parent_version_id="parent-v1",
        parent_artifact=parent_artifact(),
        gaps=(CloseGap(security_id=SecurityId(exchange=Exchange.BSE, symbol="430047"), trading_day=date(2026, 8, 28)),),
        policy_version="v1-baostock-status",
        policy_document_uri="docs/status.md",
    )

    assert result.quality_status is QualityStatus.WARN
    assert result.reconciliations[0].status is CloseGapReconciliationStatus.STATUS_UNKNOWN


def test_adapter_retries_transient_supplier_failure_with_exponential_backoff() -> None:
    class FlakyClient(FakeBaoStockClient):
        attempts = 0

        def query_history(self, code: str, start: date, end: date) -> list[dict[str, str]]:
            self.attempts += 1
            if self.attempts == 1:
                raise RuntimeError("temporary failure")
            return [{"date": "2026-08-28", "code": code, "tradestatus": "0", "isST": "0"}]

    waits: list[float] = []
    client = FlakyClient([])
    adapter = BaoStockTradingStatusAdapter(
        lambda: client,
        retry_policy=RetryPolicy(max_attempts=3, initial_backoff_seconds=0.5, min_interval_seconds=0),
        wait=waits.append,
    )

    batches = adapter.fetch(((SecurityId(exchange=Exchange.SSE, symbol="600000"), date(2026, 8, 28), date(2026, 8, 28)),))
    assert len(batches[0].rows) == 1
    assert client.attempts == 2
    assert waits == [0.5]


def test_adapter_restores_socket_timeout_after_query() -> None:
    before = socket.getdefaulttimeout()
    client = FakeBaoStockClient([{"date": "2026-08-28", "code": "sh.600000", "tradestatus": "0", "isST": "0"}])
    adapter = BaoStockTradingStatusAdapter(
        lambda: client,
        retry_policy=RetryPolicy(query_timeout_seconds=0.1, min_interval_seconds=0),
        wait=lambda _: None,
    )

    adapter.fetch(((SecurityId(exchange=Exchange.SSE, symbol="600000"), date(2026, 8, 28), date(2026, 8, 28)),))
    assert socket.getdefaulttimeout() == before


def test_status_fact_is_not_visible_before_it_was_captured() -> None:
    observed_at = datetime(2026, 8, 29, 12, tzinfo=UTC)
    adapter = BaoStockTradingStatusAdapter(
        lambda: FakeBaoStockClient([{"date": "2026-08-28", "code": "sh.600000", "tradestatus": "0", "isST": "0"}]),
        now=lambda: observed_at,
    )
    result = BaoStockStatusEnrichmentService(adapter, FakeArtifactWriter(), FakeLineage(), "minio://artifacts").enrich(
        parent_version_id="parent-v1",
        parent_artifact=parent_artifact(),
        gaps=(CloseGap(security_id=SecurityId(exchange=Exchange.SSE, symbol="600000"), trading_day=date(2026, 8, 28)),),
        policy_version="v1-baostock-status",
        policy_document_uri="docs/status.md",
    )

    assert visible_trading_status(list(result.facts), datetime(2026, 8, 29, 11, 59, tzinfo=UTC)) == []
    assert visible_trading_status(list(result.facts), observed_at) == list(result.facts)
