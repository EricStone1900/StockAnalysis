import os
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest

from src.news_events import FakeFinancialNewsAnalyzer, SecurityEntity, build_candidate
from src.news_ingestion import EvidenceArtifact, NewsItem
from src.news_repository import PostgresNewsRepository

DATABASE_URL = os.getenv("NEWS_INTELLIGENCE_DATABASE_URL")
pytestmark = pytest.mark.skipif(not DATABASE_URL, reason="NEWS_INTELLIGENCE_DATABASE_URL is not configured")


def test_migration_save_and_duplicate_lookup() -> None:
    assert DATABASE_URL is not None
    repository = PostgresNewsRepository(DATABASE_URL)
    repository.migrate(Path(__file__).parents[2] / "migrations" / "001_news.sql")
    suffix = uuid4().hex
    item = NewsItem(
        news_id=f"integration-news-{suffix}", source_id="integration-source",
        canonical_url=f"https://example.test/news/{suffix}", title="集成测试公告", language="zh-CN",
        published_at=datetime(2026, 9, 4, 1, 0, tzinfo=UTC),
        collected_at=datetime(2026, 9, 4, 1, 1, tzinfo=UTC),
        available_at=datetime(2026, 9, 4, 1, 1, tzinfo=UTC), source_reliability=0.9,
        content_hash=("a" * 63) + suffix[:1],
        evidence=EvidenceArtifact(uri=f"s3://artifacts/news/{suffix}.txt", content_hash=("a" * 63) + suffix[:1], license_policy_id="official-v1"),
    )
    repository.save(item)
    repository.save(item)
    assert repository.find_duplicate(item.canonical_url, item.content_hash) == item

    candidate = build_candidate(item.model_copy(update={"title": "星河科技公告"}), (SecurityEntity(symbol="SSE:1", name="星河科技"),))
    repository.save_candidate(candidate)
    event = FakeFinancialNewsAnalyzer().analyze(candidate, f"run-{suffix}")
    repository.save_event(event)
    repository.save_event(event)
    assert repository.find_event_by_agent_run(event.agent_run_id) == event
