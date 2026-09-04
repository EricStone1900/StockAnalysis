"""阶段06新闻采集最小切片：仅接收受控 Fixture，不访问外部新闻源。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from typing import Protocol
from urllib.parse import urldefrag

from pydantic import BaseModel, Field, HttpUrl, field_validator


class FixtureNewsInput(BaseModel):
    source_id: str = Field(min_length=1)
    source_url: HttpUrl
    title: str = Field(min_length=1)
    content: str = Field(min_length=1)
    published_at: datetime
    collected_at: datetime
    available_at: datetime
    license_policy_id: str = Field(min_length=1)
    archive_allowed: bool
    language: str = Field(min_length=2, max_length=16)
    source_reliability: float = Field(ge=0, le=1)

    @field_validator("published_at", "collected_at", "available_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("timestamp must include timezone")
        return value.astimezone(UTC)


class EvidenceArtifact(BaseModel):
    uri: str
    content_hash: str
    license_policy_id: str


class NewsItem(BaseModel):
    news_id: str
    source_id: str
    canonical_url: str
    title: str
    language: str
    published_at: datetime
    collected_at: datetime
    available_at: datetime
    source_reliability: float
    content_hash: str
    evidence: EvidenceArtifact
    status: str = "RAW"
    untrusted_content: bool = True


@dataclass(frozen=True)
class IngestionResult:
    item: NewsItem
    duplicate: bool


class EvidenceStore(Protocol):
    def put(self, content: str, content_hash: str, license_policy_id: str) -> EvidenceArtifact: ...


class NewsRepository(Protocol):
    def find_duplicate(self, canonical_url: str, content_hash: str) -> NewsItem | None: ...

    def save(self, item: NewsItem) -> None: ...


class InMemoryArtifactStore:
    """测试期证据仓库；生产替换为不可变 MinIO Adapter。"""

    def __init__(self) -> None:
        self._contents: dict[str, bytes] = {}

    def put(self, content: str, content_hash: str, license_policy_id: str) -> EvidenceArtifact:
        encoded = content.encode("utf-8")
        if sha256(encoded).hexdigest() != content_hash:
            raise ValueError("evidence content hash mismatch")
        uri = f"memory://news/{content_hash}"
        self._contents.setdefault(uri, encoded)
        return EvidenceArtifact(uri=uri, content_hash=content_hash, license_policy_id=license_policy_id)


class InMemoryNewsRepository:
    def __init__(self) -> None:
        self._by_url: dict[str, NewsItem] = {}
        self._by_hash: dict[str, NewsItem] = {}

    def find_duplicate(self, canonical_url: str, content_hash: str) -> NewsItem | None:
        return self._by_url.get(canonical_url) or self._by_hash.get(content_hash)

    def save(self, item: NewsItem) -> None:
        self._by_url[item.canonical_url] = item
        self._by_hash[item.content_hash] = item


class NewsIngestionService:
    def __init__(self, repository: NewsRepository, artifacts: EvidenceStore) -> None:
        self._repository = repository
        self._artifacts = artifacts

    def ingest_fixture(self, source: FixtureNewsInput) -> IngestionResult:
        if source.available_at < source.published_at:
            raise ValueError("available_at must not precede published_at")
        if not source.archive_allowed:
            raise ValueError("license policy forbids content archival")
        canonical_url = urldefrag(str(source.source_url))[0]
        normalized_content = source.content.strip()
        content_hash = sha256(normalized_content.encode("utf-8")).hexdigest()
        duplicate = self._repository.find_duplicate(canonical_url, content_hash)
        if duplicate is not None:
            return IngestionResult(item=duplicate, duplicate=True)
        evidence = self._artifacts.put(normalized_content, content_hash, source.license_policy_id)
        item = NewsItem(
            news_id=f"news-{content_hash[:20]}", source_id=source.source_id,
            canonical_url=canonical_url, title=source.title.strip(), language=source.language,
            published_at=source.published_at, collected_at=source.collected_at,
            available_at=source.available_at, source_reliability=source.source_reliability,
            content_hash=content_hash, evidence=evidence,
        )
        self._repository.save(item)
        return IngestionResult(item=item, duplicate=False)
