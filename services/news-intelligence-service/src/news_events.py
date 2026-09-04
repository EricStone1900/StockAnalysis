"""新闻候选事件与 Fake Analyzer 契约；不执行真实模型或交易决策。"""

from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha256

from pydantic import BaseModel, Field

from src.news_ingestion import NewsItem


class SecurityEntity(BaseModel):
    symbol: str
    name: str
    aliases: tuple[str, ...] = ()


class EntityLink(BaseModel):
    symbol: str
    confidence: float = Field(ge=0, le=1)


class NewsEventCandidate(BaseModel):
    candidate_id: str
    news_ids: tuple[str, ...]
    cluster_version: str = "rules-v1"
    representative_title: str
    content_refs: tuple[str, ...]
    candidate_symbols: tuple[EntityLink, ...]
    source_summary: tuple[str, ...]
    published_at_start: datetime
    published_at_end: datetime
    freshness: str = "FRESH"


class FinancialNewsEvent(BaseModel):
    event_id: str
    candidate_id: str
    news_ids: tuple[str, ...]
    event_type: str
    affected_symbols: tuple[str, ...]
    relevance: float = Field(ge=0, le=1)
    impact_direction: str
    impact_magnitude: str
    impact_horizon: str
    novelty_score: float = Field(ge=0, le=1)
    source_reliability: float = Field(ge=0, le=1)
    confidence: float = Field(ge=0, le=1)
    summary: str
    reasoning: str
    evidence_ids: tuple[str, ...]
    analyzed_at: datetime
    provider: str = "fake"
    model_id: str = "fake-news-v1"
    prompt_version: str = "news-prompt-v1"
    agent_run_id: str


def link_entities(item: NewsItem, entities: tuple[SecurityEntity, ...]) -> tuple[EntityLink, ...]:
    """仅接受唯一精确名称/别名命中；冲突时返回空，避免静默错配。"""
    haystack = {item.title, item.title.replace(" ", "")}
    matches: list[SecurityEntity] = []
    for entity in entities:
        terms = (entity.name, *entity.aliases)
        if any(term and any(term in value for value in haystack) for term in terms):
            matches.append(entity)
    if len(matches) != 1:
        return ()
    return (EntityLink(symbol=matches[0].symbol, confidence=0.95),)


def build_candidate(item: NewsItem, entities: tuple[SecurityEntity, ...]) -> NewsEventCandidate:
    candidate_id = "candidate-" + sha256(item.content_hash.encode()).hexdigest()[:20]
    return NewsEventCandidate(
        candidate_id=candidate_id, news_ids=(item.news_id,), representative_title=item.title,
        content_refs=(item.evidence.uri,), candidate_symbols=link_entities(item, entities),
        source_summary=(item.source_id,), published_at_start=item.published_at,
        published_at_end=item.published_at,
    )


class FakeFinancialNewsAnalyzer:
    def __init__(self) -> None:
        self._events: dict[str, FinancialNewsEvent] = {}

    def analyze(self, candidate: NewsEventCandidate, agent_run_id: str) -> FinancialNewsEvent:
        existing = self._events.get(agent_run_id)
        if existing is not None:
            return existing
        event = FinancialNewsEvent(
            event_id="event-" + sha256(candidate.candidate_id.encode()).hexdigest()[:20],
            candidate_id=candidate.candidate_id, news_ids=candidate.news_ids, event_type="OTHER",
            affected_symbols=tuple(link.symbol for link in candidate.candidate_symbols), relevance=0.5,
            impact_direction="UNCERTAIN", impact_magnitude="LOW", impact_horizon="SHORT_TERM",
            novelty_score=1.0, source_reliability=1.0, confidence=0.0,
            summary="Fake Analyzer 未进行事实判断", reasoning="仅用于契约和幂等验证",
            evidence_ids=candidate.content_refs, analyzed_at=datetime.now(UTC), agent_run_id=agent_run_id,
        )
        self._events[agent_run_id] = event
        return event
