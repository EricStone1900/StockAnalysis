from src.news_events import (
    FakeFinancialNewsAnalyzer,
    SecurityEntity,
    build_candidate,
    link_entities,
)
from src.news_ingestion import EvidenceArtifact, NewsItem


def item(title: str = "星河科技发布公告") -> NewsItem:
    return NewsItem(
        news_id="n-1", source_id="official", canonical_url="https://example.test/1", title=title,
        language="zh-CN", published_at="2026-09-04T01:00:00Z", collected_at="2026-09-04T01:01:00Z",
        available_at="2026-09-04T01:01:00Z", source_reliability=1, content_hash="a" * 64,
        evidence=EvidenceArtifact(uri="s3://a/news/a.txt", content_hash="a" * 64, license_policy_id="v1"),
    )


def test_entity_linker_rejects_ambiguous_alias() -> None:
    entities = (SecurityEntity(symbol="SSE:1", name="星河科技", aliases=("星河",)), SecurityEntity(symbol="SSE:2", name="银河科技", aliases=("星河",)))
    assert link_entities(item(), entities) == ()


def test_candidate_and_fake_analyzer_are_traceable_and_idempotent() -> None:
    candidate = build_candidate(item(), (SecurityEntity(symbol="SSE:1", name="星河科技"),))
    analyzer = FakeFinancialNewsAnalyzer()
    first = analyzer.analyze(candidate, "run-1")
    repeated = analyzer.analyze(candidate, "run-1")
    assert first == repeated
    assert first.evidence_ids == candidate.content_refs
    assert first.affected_symbols == ("SSE:1",)
