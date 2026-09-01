import os
from datetime import UTC, datetime
from pathlib import Path

import psycopg
import pytest

from market_data.domain import Exchange, Security, SecurityId, SecurityStatus
from market_data.lineage import FieldProvenance, ProvenanceRole
from market_data.pit import RawArtifact
from market_data.repository import (
    ConcurrentUpdateError,
    PostgresSecurityRepository,
    PostgresSourceLineageRepository,
    PostgresStatusBatchRepository,
    SourcePolicy,
)
from market_data.status_batches import plan_status_batches
from market_data.status_enrichment import CloseGap
from market_data.trading_status import (
    CloseGapReconciliation,
    CloseGapReconciliationStatus,
    TradingStatus,
    TradingStatusFact,
)


@pytest.mark.skipif("MARKET_DATA_DATABASE_URL" not in os.environ, reason="requires local PostgreSQL")
def test_security_repository_enforces_versioned_updates() -> None:
    repository = PostgresSecurityRepository(os.environ["MARKET_DATA_DATABASE_URL"])
    migration = Path(__file__).parents[2] / "migrations/001_security_calendar.sql"
    repository.migrate(migration)
    security_id = SecurityId(exchange=Exchange.SSE, symbol="600777")
    with psycopg.connect(os.environ["MARKET_DATA_DATABASE_URL"], autocommit=True) as connection:
        connection.execute("DELETE FROM close_gap_reconciliations WHERE security_id = %s", ("SSE:600777",))
        connection.execute("DELETE FROM trading_status_facts WHERE security_id = %s", ("SSE:600777",))
        connection.execute("DELETE FROM securities WHERE security_id = %s", ("SSE:600777",))
    repository.save(Security(security_id=security_id, name="浦发银行"))
    updated = repository.update_status(security_id, SecurityStatus.SUSPENDED, expected_version=1)
    assert updated.status is SecurityStatus.SUSPENDED
    assert updated.version == 2
    with pytest.raises(ConcurrentUpdateError):
        repository.update_status(security_id, SecurityStatus.DELISTED, expected_version=1)


@pytest.mark.skipif("MARKET_DATA_DATABASE_URL" not in os.environ, reason="requires local PostgreSQL")
def test_source_lineage_migration_preserves_financial_revision_constraints() -> None:
    migration_dir = Path(__file__).parents[2] / "migrations"
    with psycopg.connect(os.environ["MARKET_DATA_DATABASE_URL"], autocommit=True) as connection:
        connection.execute((migration_dir / "001_security_calendar.sql").read_text())
        connection.execute((migration_dir / "002_source_lineage.sql").read_text())
        connection.execute("DELETE FROM financial_facts WHERE raw_artifact_hash = %s", ("1" * 64,))
        connection.execute("DELETE FROM raw_artifacts WHERE raw_artifact_hash = %s", ("1" * 64,))
        connection.execute("DELETE FROM source_policies WHERE policy_version = %s", ("test-financial-v1",))
        connection.execute("DELETE FROM securities WHERE security_id = %s", ("SSE:600778",))
        connection.execute(
            "INSERT INTO securities (security_id, exchange, symbol, name, status) VALUES (%s, %s, %s, %s, %s)",
            ("SSE:600778", "SSE", "600778", "测试证券", "ACTIVE"),
        )
        connection.execute(
            "INSERT INTO source_policies (policy_version, primary_source, policy_document_uri) VALUES (%s, %s, %s)",
            ("test-financial-v1", "investment_data", "docs://source-policy/v1"),
        )
        connection.execute(
            """INSERT INTO raw_artifacts (
            raw_artifact_hash, source, source_record_id, source_version, raw_artifact_uri,
            license_ref, source_policy_version, ingested_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, now())""",
            ("1" * 64, "cninfo", "notice-1", "2026-04-01", "minio://artifacts/raw/notice-1.pdf", "cninfo-disclosure", "test-financial-v1"),
        )
        connection.execute(
            """INSERT INTO financial_facts (
            security_id, fact_type, period_end, value, announced_at, available_at, revision, raw_artifact_hash
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
            ("SSE:600778", "revenue", "2025-12-31", "100", "2026-03-01T00:00:00Z", "2026-03-02T00:00:00Z", 1, "1" * 64),
        )
        with pytest.raises(psycopg.IntegrityError):
            connection.execute(
                """INSERT INTO financial_facts (
                security_id, fact_type, period_end, value, announced_at, available_at, revision, raw_artifact_hash
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                ("SSE:600778", "revenue", "2025-12-31", "120", "2026-04-01T00:00:00Z", "2026-04-02T00:00:00Z", 2, "1" * 64),
            )


@pytest.mark.skipif("MARKET_DATA_DATABASE_URL" not in os.environ, reason="requires local PostgreSQL")
def test_source_lineage_repository_is_idempotent_and_rejects_provenance_rewrite() -> None:
    migration_dir = Path(__file__).parents[2] / "migrations"
    with psycopg.connect(os.environ["MARKET_DATA_DATABASE_URL"], autocommit=True) as connection:
        connection.execute((migration_dir / "001_security_calendar.sql").read_text())
        connection.execute((migration_dir / "002_source_lineage.sql").read_text())
        connection.execute("DELETE FROM raw_artifacts WHERE raw_artifact_hash = %s", ("2" * 64,))
        connection.execute("DELETE FROM source_policies WHERE policy_version = %s", ("test-lineage-v1",))
    repository = PostgresSourceLineageRepository(os.environ["MARKET_DATA_DATABASE_URL"])
    policy = SourcePolicy(
        policy_version="test-lineage-v1", primary_source="investment_data", policy_document_uri="docs://source-policy/v1"
    )
    artifact = RawArtifact(
        source="investment_data",
        source_record_id="2026-08-28/qlib_bin.tar.gz",
        source_version="b" * 40,
        source_release_tag="2026-08-28",
        raw_artifact_uri="minio://artifacts/raw/investment_data/2026-08-28/archive.tar.gz",
        raw_artifact_hash="2" * 64,
        license_ref="https://example.test/license",
        source_policy_version="test-lineage-v1",
        ingested_at=datetime.now(UTC),
    )

    repository.ensure_policy(policy)
    repository.ensure_policy(policy)
    repository.save_raw_artifact(artifact)
    repository.save_raw_artifact(artifact)

    with pytest.raises(ValueError, match="immutable"):
        repository.ensure_policy(
            SourcePolicy(policy_version="test-lineage-v1", primary_source="other", policy_document_uri="docs://source-policy/v1")
        )
    with pytest.raises(ValueError, match="different provenance"):
        repository.save_raw_artifact(artifact.model_copy(update={"source_record_id": "rewritten"}))


@pytest.mark.skipif("MARKET_DATA_DATABASE_URL" not in os.environ, reason="requires local PostgreSQL")
def test_trading_status_and_gap_reconciliation_persist_with_field_provenance() -> None:
    migration_dir = Path(__file__).parents[2] / "migrations"
    with psycopg.connect(os.environ["MARKET_DATA_DATABASE_URL"], autocommit=True) as connection:
        for migration in sorted(migration_dir.glob("[0-9][0-9][0-9]_*.sql")):
            connection.execute(migration.read_text())
        connection.execute("DELETE FROM close_gap_reconciliations WHERE security_id = %s", ("SSE:600099",))
        connection.execute("DELETE FROM trading_status_facts WHERE security_id = %s", ("SSE:600099",))
        connection.execute("DELETE FROM field_provenance WHERE entity_key LIKE %s", ("SSE:600099:%",))
        connection.execute("DELETE FROM raw_artifacts WHERE raw_artifact_hash IN (%s, %s)", ("e" * 64, "f" * 64))
        connection.execute("DELETE FROM source_policies WHERE policy_version IN (%s, %s)", ("test-status-primary-v1", "test-status-baostock-v1"))
        connection.execute("DELETE FROM securities WHERE security_id = %s", ("SSE:600099",))
        connection.execute(
            "INSERT INTO securities (security_id, exchange, symbol, name, status) VALUES (%s, %s, %s, %s, %s)",
            ("SSE:600099", "SSE", "600099", "状态测试", "ACTIVE"),
        )
    repository = PostgresSourceLineageRepository(os.environ["MARKET_DATA_DATABASE_URL"])
    repository.ensure_policy(SourcePolicy(policy_version="test-status-primary-v1", primary_source="investment_data", policy_document_uri="docs://primary"))
    repository.ensure_policy(SourcePolicy(policy_version="test-status-baostock-v1", primary_source="baostock", policy_document_uri="docs://status"))
    primary = RawArtifact(source="investment_data", source_record_id="release", source_version="sha", raw_artifact_uri="minio://artifacts/raw/primary", raw_artifact_hash="e" * 64, license_ref="license", source_policy_version="test-status-primary-v1", ingested_at=datetime.now(UTC))
    supplement = RawArtifact(source="baostock", source_record_id="query", source_version="status-v1", raw_artifact_uri="minio://artifacts/raw/status", raw_artifact_hash="f" * 64, license_ref="license", source_policy_version="test-status-baostock-v1", ingested_at=datetime.now(UTC))
    repository.save_raw_artifact(primary)
    repository.save_raw_artifact(supplement)
    security_id = SecurityId(exchange=Exchange.SSE, symbol="600099")
    status_provenance = FieldProvenance(field_name="trading_status", source="baostock", source_record_id="query:1", raw_artifact_hash="f" * 64, source_version="status-v1", source_policy_version="test-status-baostock-v1", role=ProvenanceRole.SUPPLEMENT)
    fact = TradingStatusFact(security_id=security_id, trading_day=datetime(2026, 8, 28, tzinfo=UTC).date(), trading_status=TradingStatus.SUSPENDED, raw_tradestatus="0", observed_at=datetime.now(UTC), available_at=datetime.now(UTC), artifact=supplement, field_provenance=(status_provenance,))
    repository.save_trading_status_fact(fact)
    close_provenance = FieldProvenance(field_name="close", source="investment_data", source_record_id="release:1", raw_artifact_hash="e" * 64, source_version="sha", source_policy_version="test-status-primary-v1", role=ProvenanceRole.PRIMARY)
    repository.save_close_gap_reconciliation(CloseGapReconciliation(security_id=security_id, trading_day=fact.trading_day, status=CloseGapReconciliationStatus.SUSPENSION_CONFIRMED, reason="baostock_tradestatus_0", primary_provenance=close_provenance, status_provenance=status_provenance), "test-status-baostock-v1")
    with psycopg.connect(os.environ["MARKET_DATA_DATABASE_URL"]) as connection:
        assert connection.execute("SELECT trading_status FROM trading_status_facts WHERE security_id = %s", ("SSE:600099",)).fetchone() == ("SUSPENDED",)
        assert connection.execute("SELECT status FROM close_gap_reconciliations WHERE security_id = %s", ("SSE:600099",)).fetchone() == ("SUSPENSION_CONFIRMED",)
        assert connection.execute("SELECT count(*) FROM field_provenance WHERE entity_key LIKE %s", ("SSE:600099:%",)).fetchone() == (3,)


@pytest.mark.skipif("MARKET_DATA_DATABASE_URL" not in os.environ, reason="requires local PostgreSQL")
def test_status_batch_repository_claims_retries_and_prevents_duplicate_success() -> None:
    migration_dir = Path(__file__).parents[2] / "migrations"
    parent_version_id = "test-batch-parent-v1"
    policy_version = "test-status-batch-v1"
    with psycopg.connect(os.environ["MARKET_DATA_DATABASE_URL"], autocommit=True) as connection:
        for migration in sorted(migration_dir.glob("[0-9][0-9][0-9]_*.sql")):
            connection.execute(migration.read_text())
        connection.execute("DELETE FROM status_enrichment_batches WHERE parent_version_id = %s", (parent_version_id,))
        connection.execute("DELETE FROM source_policies WHERE policy_version = %s", (policy_version,))
    lineage = PostgresSourceLineageRepository(os.environ["MARKET_DATA_DATABASE_URL"])
    lineage.ensure_policy(SourcePolicy(policy_version=policy_version, primary_source="baostock", policy_document_uri="docs://test-batch"))
    batches = plan_status_batches(
        (
            CloseGap(security_id=SecurityId(exchange=Exchange.SSE, symbol="600000"), trading_day=datetime(2025, 1, 2, tzinfo=UTC).date()),
            CloseGap(security_id=SecurityId(exchange=Exchange.SSE, symbol="600001"), trading_day=datetime(2025, 1, 2, tzinfo=UTC).date()),
        ),
        1,
    )
    repository = PostgresStatusBatchRepository(os.environ["MARKET_DATA_DATABASE_URL"])
    repository.ensure_batches(parent_version_id, policy_version, batches)
    batch_id = batches[0].batch_id

    assert repository.claim(batch_id)
    assert not repository.claim(batch_id)
    repository.mark_failed(batch_id, "transient timeout")
    assert repository.claim(batch_id)
    repository.mark_succeeded(batch_id)
    assert not repository.claim(batch_id)

    with psycopg.connect(os.environ["MARKET_DATA_DATABASE_URL"]) as connection:
        assert connection.execute("SELECT state, attempts, last_error FROM status_enrichment_batches WHERE batch_id = %s", (batch_id,)).fetchone() == ("SUCCEEDED", 2, None)
