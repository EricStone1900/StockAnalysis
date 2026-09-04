"""新闻 PostgreSQL 与对象存储适配器；不包含任何外部抓取逻辑。"""

from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path

import psycopg
from boto3.session import Session

from src.news_ingestion import EvidenceArtifact, NewsItem


class PostgresNewsRepository:
    def __init__(self, database_url: str) -> None:
        self._database_url = database_url

    def migrate(self, migration: Path) -> None:
        with psycopg.connect(self._database_url, autocommit=True) as connection:
            connection.execute(migration.read_text())

    def find_duplicate(self, canonical_url: str, content_hash: str) -> NewsItem | None:
        with psycopg.connect(self._database_url) as connection:
            row = connection.execute(
                "SELECT payload FROM news_items WHERE canonical_url = %s OR content_hash = %s ORDER BY created_at LIMIT 1",
                (canonical_url, content_hash),
            ).fetchone()
        return NewsItem.model_validate(row[0]) if row else None

    def save(self, item: NewsItem) -> None:
        payload = item.model_dump(mode="json")
        with psycopg.connect(self._database_url) as connection:
            connection.execute(
                """INSERT INTO news_items (
                news_id, source_id, canonical_url, title, language, published_at, collected_at,
                available_at, source_reliability, content_hash, evidence_uri, license_policy_id,
                status, payload
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
                ON CONFLICT DO NOTHING""",
                (
                    item.news_id, item.source_id, item.canonical_url, item.title, item.language,
                    item.published_at, item.collected_at, item.available_at, item.source_reliability,
                    item.content_hash, item.evidence.uri, item.evidence.license_policy_id,
                    item.status, json.dumps(payload),
                ),
            )


class MinioEvidenceStore:
    """按正文 Hash 写入不可变对象，避免同一键静默覆盖。"""

    def __init__(self, endpoint_url: str, access_key: str, secret_key: str, bucket: str) -> None:
        self._bucket = bucket
        self._client = Session().client(
            "s3", endpoint_url=endpoint_url, aws_access_key_id=access_key, aws_secret_access_key=secret_key,
        )

    def put(self, content: str, content_hash: str, license_policy_id: str) -> EvidenceArtifact:
        encoded = content.encode("utf-8")
        if sha256(encoded).hexdigest() != content_hash:
            raise ValueError("evidence content hash mismatch")
        key = f"news/{content_hash}.txt"
        try:
            existing = self._client.head_object(Bucket=self._bucket, Key=key)
        except Exception as error:
            response = getattr(error, "response", None)
            code = response.get("Error", {}).get("Code") if isinstance(response, dict) else None
            if code not in {"404", "NoSuchKey", "NotFound"}:
                raise
        else:
            if existing.get("Metadata", {}).get("sha256") != content_hash:
                raise ValueError("immutable evidence key contains different content")
            return EvidenceArtifact(uri=f"s3://{self._bucket}/{key}", content_hash=content_hash, license_policy_id=license_policy_id)
        self._client.put_object(Bucket=self._bucket, Key=key, Body=encoded, Metadata={"sha256": content_hash})
        return EvidenceArtifact(uri=f"s3://{self._bucket}/{key}", content_hash=content_hash, license_policy_id=license_policy_id)


def verify_evidence_content(content: bytes, expected_hash: str) -> None:
    if sha256(content).hexdigest() != expected_hash:
        raise ValueError("evidence content hash mismatch")
