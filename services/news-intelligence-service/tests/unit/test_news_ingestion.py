from datetime import datetime

import pytest

from src.news_ingestion import (
    FixtureNewsInput,
    InMemoryArtifactStore,
    InMemoryNewsRepository,
    NewsIngestionService,
)


def fixture(**changes: object) -> FixtureNewsInput:
    values: dict[str, object] = {
        "source_id": "exchange", "source_url": "https://example.test/news/1#fragment",
        "title": "公告", "content": " 原始正文 ", "published_at": "2026-09-04T01:00:00+08:00",
        "collected_at": "2026-09-04T01:05:00+08:00", "available_at": "2026-09-04T01:05:00+08:00",
        "license_policy_id": "official-v1", "archive_allowed": True, "language": "zh-CN",
        "source_reliability": 0.9,
    }
    values.update(changes)
    return FixtureNewsInput.model_validate(values)


def test_ingestion_stores_immutable_evidence_and_is_idempotent() -> None:
    service = NewsIngestionService(InMemoryNewsRepository(), InMemoryArtifactStore())
    first = service.ingest_fixture(fixture())
    repeated = service.ingest_fixture(fixture(source_url="https://example.test/news/1"))
    assert first.duplicate is False
    assert first.item.evidence.uri.startswith("memory://news/")
    assert first.item.untrusted_content is True
    assert repeated.duplicate is True
    assert repeated.item.news_id == first.item.news_id


def test_ingestion_rejects_forbidden_license_and_invalid_time_order() -> None:
    service = NewsIngestionService(InMemoryNewsRepository(), InMemoryArtifactStore())
    with pytest.raises(ValueError, match="forbids"):
        service.ingest_fixture(fixture(archive_allowed=False))
    with pytest.raises(ValueError, match="available_at"):
        service.ingest_fixture(fixture(available_at=datetime.fromisoformat("2026-09-03T01:00:00+08:00")))
