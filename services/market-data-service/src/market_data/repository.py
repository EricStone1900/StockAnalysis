from collections.abc import Iterable
from pathlib import Path
from typing import Any

import psycopg
from pydantic import BaseModel, Field

from .domain import Security, SecurityId, SecurityStatus
from .lineage import FieldProvenance
from .pit import RawArtifact
from .status_batches import StatusBatch, StatusBatchState
from .trading_status import CloseGapReconciliation, TradingStatusFact
from .versioning import DataVersion


class PostgresSecurityRepository:
    def __init__(self, database_url: str) -> None:
        self.database_url = database_url

    def migrate(self, migration: Path) -> None:
        with psycopg.connect(self.database_url, autocommit=True) as connection:
            connection.execute(migration.read_text())

    def save(self, security: Security) -> None:
        with psycopg.connect(self.database_url) as connection:
            connection.execute(
                "INSERT INTO securities (security_id, exchange, symbol, name, status) VALUES (%s, %s, %s, %s, %s)",
                (self._key(security.security_id), security.security_id.exchange, security.security_id.symbol, security.name, security.status),
            )

    def get(self, symbol: str) -> Security | None:
        with psycopg.connect(self.database_url) as connection:
            row = connection.execute("SELECT exchange, symbol, name, status, version FROM securities WHERE symbol = %s", (symbol,)).fetchone()
        if row is None:
            return None
        exchange, stored_symbol, name, status, version = row
        return Security(security_id=SecurityId(exchange=exchange, symbol=stored_symbol), name=name, status=SecurityStatus(status), version=version)

    def update_status(self, security_id: SecurityId, status: SecurityStatus, expected_version: int) -> Security:
        with psycopg.connect(self.database_url) as connection:
            row = connection.execute(
                """UPDATE securities
                SET status = %s, version = version + 1
                WHERE security_id = %s AND version = %s
                RETURNING exchange, symbol, name, status, version""",
                (status, self._key(security_id), expected_version),
            ).fetchone()
        if row is None:
            raise ConcurrentUpdateError(self._key(security_id))
        exchange, symbol, name, stored_status, version = row
        return Security(security_id=SecurityId(exchange=exchange, symbol=symbol), name=name, status=SecurityStatus(stored_status), version=version)

    @staticmethod
    def _key(security_id: SecurityId) -> str:
        return f"{security_id.exchange}:{security_id.symbol}"


class ConcurrentUpdateError(ValueError):
    pass


class SourcePolicy(BaseModel):
    policy_version: str = Field(min_length=1)
    primary_source: str = Field(min_length=1)
    policy_document_uri: str = Field(min_length=1)


class PostgresSourceLineageRepository:
    """来源元数据以追加方式保存；同一Hash或策略版本不能被静默改写。"""

    def __init__(self, database_url: str) -> None:
        self.database_url = database_url

    def ensure_policy(self, policy: SourcePolicy) -> None:
        with psycopg.connect(self.database_url) as connection:
            connection.execute(
                """INSERT INTO source_policies (policy_version, primary_source, policy_document_uri)
                VALUES (%s, %s, %s) ON CONFLICT (policy_version) DO NOTHING""",
                (policy.policy_version, policy.primary_source, policy.policy_document_uri),
            )
            row = connection.execute(
                "SELECT primary_source, policy_document_uri FROM source_policies WHERE policy_version = %s",
                (policy.policy_version,),
            ).fetchone()
        if row != (policy.primary_source, policy.policy_document_uri):
            raise ValueError("source policy version is immutable")

    def ensure_securities(self, security_ids: object) -> None:
        """Qlib股票池不带正式名称，仅创建不覆盖既有名称的明确占位主数据。"""
        from collections.abc import Iterable

        if not isinstance(security_ids, Iterable):
            raise TypeError("security_ids must be iterable")
        rows = []
        for security_id in security_ids:
            if not isinstance(security_id, SecurityId):
                raise TypeError("security_ids must contain SecurityId")
            rows.append(
                (
                    PostgresSecurityRepository._key(security_id),
                    security_id.exchange,
                    security_id.symbol,
                    f"待补全:{security_id.symbol}",
                    SecurityStatus.ACTIVE,
                )
            )
        if not rows:
            return
        with psycopg.connect(self.database_url) as connection, connection.cursor() as cursor:
            cursor.executemany(
                """INSERT INTO securities (security_id, exchange, symbol, name, status)
                VALUES (%s, %s, %s, %s, %s) ON CONFLICT (security_id) DO NOTHING""",
                rows,
            )

    def save_raw_artifact(self, artifact: RawArtifact) -> None:
        with psycopg.connect(self.database_url) as connection:
            connection.execute(
                """INSERT INTO raw_artifacts (
                raw_artifact_hash, source, source_record_id, source_version, source_release_tag,
                raw_artifact_uri, license_ref, source_policy_version, ingested_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (raw_artifact_hash) DO NOTHING""",
                (
                    artifact.raw_artifact_hash,
                    artifact.source,
                    artifact.source_record_id,
                    artifact.source_version,
                    artifact.source_release_tag,
                    artifact.raw_artifact_uri,
                    artifact.license_ref,
                    artifact.source_policy_version,
                    artifact.ingested_at,
                ),
            )
            row = connection.execute(
                """SELECT source, source_record_id, source_version, source_release_tag,
                raw_artifact_uri, license_ref, source_policy_version
                FROM raw_artifacts WHERE raw_artifact_hash = %s""",
                (artifact.raw_artifact_hash,),
            ).fetchone()
        expected = (
            artifact.source,
            artifact.source_record_id,
            artifact.source_version,
            artifact.source_release_tag,
            artifact.raw_artifact_uri,
            artifact.license_ref,
            artifact.source_policy_version,
        )
        if row != expected:
            raise ValueError("raw artifact hash is already associated with different provenance")

    def save_data_version(self, version: DataVersion) -> None:
        """以版本ID幂等保存版本元数据，支持后续索引回填。"""
        with psycopg.connect(self.database_url) as connection:
            connection.execute(
                """INSERT INTO data_versions (
                version_id, status, scope, source_version, source_release_tag,
                source_policy_version, source_manifest_hash, artifact_uri, artifact_hash,
                quality_report_uri, close_gap_index_uri, close_gap_index_hash,
                quality_status, available_at, content_hash, parent_version_id
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (version_id) DO NOTHING""",
                (version.version_id, version.status, version.scope, version.source_version,
                 version.source_release_tag, version.source_policy_version, version.source_manifest_hash,
                 version.artifact_uri, version.artifact_hash, version.quality_report_uri,
                 version.close_gap_index_uri, version.close_gap_index_hash, version.quality_status,
                 version.available_at, version.content_hash, version.parent_version_id),
            )

    def get_data_version(self, version_id: str) -> DataVersion | None:
        with psycopg.connect(self.database_url) as connection:
            row = connection.execute(
                """SELECT version_id, status, scope, source_version, source_release_tag,
                source_policy_version, source_manifest_hash, artifact_uri, artifact_hash,
                quality_report_uri, close_gap_index_uri, close_gap_index_hash,
                quality_status, available_at, content_hash, parent_version_id
                FROM data_versions WHERE version_id = %s""",
                (version_id,),
            ).fetchone()
        return self._data_version_from_row(row)

    def latest_ready_data_version(self) -> DataVersion | None:
        """为跨服务只读API恢复重启前已持久化的READY版本。"""
        with psycopg.connect(self.database_url) as connection:
            row = connection.execute(
                """SELECT version_id, status, scope, source_version, source_release_tag,
                source_policy_version, source_manifest_hash, artifact_uri, artifact_hash,
                quality_report_uri, close_gap_index_uri, close_gap_index_hash,
                quality_status, available_at, content_hash, parent_version_id
                FROM data_versions WHERE status = 'READY'
                ORDER BY available_at DESC, version_id DESC LIMIT 1"""
            ).fetchone()
        return self._data_version_from_row(row)

    @staticmethod
    def _data_version_from_row(row: tuple[Any, ...] | None) -> DataVersion | None:
        if row is None:
            return None
        return DataVersion(
            version_id=row[0], status=row[1], scope=row[2], source_version=row[3],
            source_release_tag=row[4], source_policy_version=row[5], source_manifest_hash=row[6],
            artifact_uri=row[7], artifact_hash=row[8], quality_report_uri=row[9],
            close_gap_index_uri=row[10], close_gap_index_hash=row[11], quality_status=row[12],
            available_at=row[13], content_hash=row[14], parent_version_id=row[15],
        )

    def attach_close_gap_index(self, version_id: str, index_uri: str, index_hash: str) -> None:
        if len(index_hash) != 64:
            raise ValueError("close gap index hash must be SHA-256")
        with psycopg.connect(self.database_url) as connection:
            row = connection.execute(
                """UPDATE data_versions
                SET close_gap_index_uri = COALESCE(close_gap_index_uri, %s),
                    close_gap_index_hash = COALESCE(close_gap_index_hash, %s)
                WHERE version_id = %s
                RETURNING close_gap_index_uri, close_gap_index_hash""",
                (index_uri, index_hash, version_id),
            ).fetchone()
        if row is None:
            raise ValueError("data version does not exist")
        if row != (index_uri, index_hash):
            raise ValueError("close gap index is already attached with different provenance")

    def save_trading_status_fact(self, fact: TradingStatusFact) -> None:
        security_key = PostgresSecurityRepository._key(fact.security_id)
        with psycopg.connect(self.database_url) as connection:
            connection.execute(
                """INSERT INTO trading_status_facts (
                security_id, trading_day, trading_status, is_st, raw_tradestatus, raw_is_st,
                observed_at, available_at, raw_artifact_hash
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING""",
                (
                    security_key,
                    fact.trading_day,
                    fact.trading_status,
                    fact.is_st,
                    fact.raw_tradestatus,
                    fact.raw_is_st,
                    fact.observed_at,
                    fact.available_at,
                    fact.artifact.raw_artifact_hash,
                ),
            )
            for provenance in fact.field_provenance:
                self._save_field_provenance(
                    connection,
                    entity_type="trading_status_fact",
                    entity_key=f"{security_key}:{fact.trading_day.isoformat()}",
                    provenance=provenance,
                )

    def save_close_gap_reconciliation(self, reconciliation: CloseGapReconciliation, policy_version: str) -> None:
        security_key = PostgresSecurityRepository._key(reconciliation.security_id)
        with psycopg.connect(self.database_url) as connection:
            connection.execute(
                """INSERT INTO close_gap_reconciliations (
                policy_version, security_id, trading_day, status, reason,
                primary_raw_artifact_hash, status_raw_artifact_hash
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (policy_version, security_id, trading_day) DO NOTHING""",
                (
                    policy_version,
                    security_key,
                    reconciliation.trading_day,
                    reconciliation.status,
                    reconciliation.reason,
                    reconciliation.primary_provenance.raw_artifact_hash,
                    (
                        reconciliation.status_provenance.raw_artifact_hash
                        if reconciliation.status_provenance is not None
                        else None
                    ),
                ),
            )
            self._save_field_provenance(
                connection,
                entity_type="close_gap_reconciliation",
                entity_key=f"{security_key}:{reconciliation.trading_day.isoformat()}",
                provenance=reconciliation.primary_provenance,
            )
            if reconciliation.status_provenance is not None:
                self._save_field_provenance(
                    connection,
                    entity_type="close_gap_reconciliation",
                    entity_key=f"{security_key}:{reconciliation.trading_day.isoformat()}",
                    provenance=reconciliation.status_provenance,
                )

    def save_close_gap_reconciliations(
        self, reconciliations: Iterable[CloseGapReconciliation], policy_version: str
    ) -> None:
        """批量写入停牌空洞核验，避免全量假设模式逐条建连。"""
        items = tuple(reconciliations)
        if not items:
            return
        with psycopg.connect(self.database_url) as connection:
            with connection.cursor() as cursor:
                cursor.executemany(
                """INSERT INTO close_gap_reconciliations (
                policy_version, security_id, trading_day, status, reason,
                primary_raw_artifact_hash, status_raw_artifact_hash
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (policy_version, security_id, trading_day) DO NOTHING""",
                    [
                    (
                        policy_version,
                        PostgresSecurityRepository._key(item.security_id),
                        item.trading_day,
                        item.status,
                        item.reason,
                        item.primary_provenance.raw_artifact_hash,
                        item.status_provenance.raw_artifact_hash if item.status_provenance else None,
                    )
                    for item in items
                    ],
                )
            provenance_rows = []
            for item in items:
                security_key = PostgresSecurityRepository._key(item.security_id)
                entity_key = f"{security_key}:{item.trading_day.isoformat()}"
                provenance_rows.append((entity_key, item.primary_provenance))
                if item.status_provenance:
                    provenance_rows.append((entity_key, item.status_provenance))
            with connection.cursor() as cursor:
                cursor.executemany(
                """INSERT INTO field_provenance (
                entity_type, entity_key, field_name, source, source_record_id, raw_artifact_hash,
                source_version, source_policy_version, role
                ) VALUES ('close_gap_reconciliation', %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING""",
                    [
                    (
                        entity_key,
                        provenance.field_name,
                        provenance.source,
                        provenance.source_record_id,
                        provenance.raw_artifact_hash,
                        provenance.source_version,
                        provenance.source_policy_version,
                        provenance.role,
                    )
                    for entity_key, provenance in provenance_rows
                    ],
                )

    @staticmethod
    def _save_field_provenance(
        connection: psycopg.Connection[object], *, entity_type: str, entity_key: str, provenance: FieldProvenance
    ) -> None:
        connection.execute(
            """INSERT INTO field_provenance (
            entity_type, entity_key, field_name, source, source_record_id, raw_artifact_hash,
            source_version, source_policy_version, role
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING""",
            (
                entity_type,
                entity_key,
                provenance.field_name,
                provenance.source,
                provenance.source_record_id,
                provenance.raw_artifact_hash,
                provenance.source_version,
                provenance.source_policy_version,
                provenance.role,
            ),
        )


class PostgresStatusBatchRepository:
    """批次计划与状态以数据库为准，领取操作在并发执行器之间原子化。"""

    def __init__(self, database_url: str) -> None:
        self.database_url = database_url

    def ensure_batches(self, parent_version_id: str, policy_version: str, batches: tuple[StatusBatch, ...]) -> None:
        with psycopg.connect(self.database_url) as connection, connection.cursor() as cursor:
            for batch in batches:
                cursor.execute(
                    """INSERT INTO status_enrichment_batches (
                    batch_id, parent_version_id, policy_version, ordinal, gap_count, first_key, last_key, state
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (batch_id) DO NOTHING""",
                    (
                        batch.batch_id,
                        parent_version_id,
                        policy_version,
                        batch.ordinal,
                        batch.gap_count,
                        batch.first_key,
                        batch.last_key,
                        StatusBatchState.PENDING,
                    ),
                )
                row = cursor.execute(
                    """SELECT parent_version_id, policy_version, ordinal, gap_count, first_key, last_key
                    FROM status_enrichment_batches WHERE batch_id = %s""",
                    (batch.batch_id,),
                ).fetchone()
                expected = (
                    parent_version_id,
                    policy_version,
                    batch.ordinal,
                    batch.gap_count,
                    batch.first_key,
                    batch.last_key,
                )
                if row != expected:
                    raise ValueError("status batch identity is immutable")

    def claim(self, batch_id: str) -> bool:
        with psycopg.connect(self.database_url) as connection:
            row = connection.execute(
                """UPDATE status_enrichment_batches
                SET state = %s, attempts = attempts + 1, started_at = now(), completed_at = NULL, last_error = NULL
                WHERE batch_id = %s AND state IN (%s, %s)
                RETURNING batch_id""",
                (StatusBatchState.RUNNING, batch_id, StatusBatchState.PENDING, StatusBatchState.FAILED),
            ).fetchone()
        return row is not None

    def mark_succeeded(self, batch_id: str) -> None:
        self._complete(batch_id, StatusBatchState.SUCCEEDED, None)

    def mark_failed(self, batch_id: str, error: str) -> None:
        self._complete(batch_id, StatusBatchState.FAILED, error[:1000])

    def _complete(self, batch_id: str, state: StatusBatchState, error: str | None) -> None:
        with psycopg.connect(self.database_url) as connection:
            row = connection.execute(
                """UPDATE status_enrichment_batches
                SET state = %s, last_error = %s, completed_at = now()
                WHERE batch_id = %s AND state = %s
                RETURNING batch_id""",
                (state, error, batch_id, StatusBatchState.RUNNING),
            ).fetchone()
        if row is None:
            raise ValueError("status batch must be running before completion")
