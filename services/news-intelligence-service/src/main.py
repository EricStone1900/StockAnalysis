import os
from pathlib import Path
from typing import Any, cast

from fastapi import FastAPI, HTTPException

from src.news_events import (
    FakeFinancialNewsAnalyzer,
    NewsEventCandidate,
    SecurityEntity,
    build_candidate,
    freshness_for,
)
from src.news_ingestion import (
    FixtureNewsInput,
    InMemoryArtifactStore,
    InMemoryNewsRepository,
    NewsIngestionService,
)
from src.news_repository import MinioEvidenceStore, PostgresNewsRepository

app = FastAPI(title="news-intelligence-service", version="0.1.0")


def _read_optional_secret(value: str | None, file_name: str | None) -> str | None:
    if value:
        return value
    return Path(file_name).read_text().strip() if file_name else None


def build_ingestion_service() -> NewsIngestionService:
    database_url = os.getenv("NEWS_INTELLIGENCE_DATABASE_URL")
    endpoint = os.getenv("MINIO_ENDPOINT")
    access_key = os.getenv("MINIO_ACCESS_KEY")
    secret_key = _read_optional_secret(os.getenv("MINIO_SECRET_KEY"), os.getenv("MINIO_SECRET_KEY_FILE"))
    bucket = os.getenv("ARTIFACT_BUCKET")
    configured = [database_url, endpoint, access_key, secret_key, bucket]
    if not any(configured):
        return NewsIngestionService(InMemoryNewsRepository(), InMemoryArtifactStore())
    if not all(configured):
        raise RuntimeError("news persistence configuration is incomplete")
    assert database_url and endpoint and access_key and secret_key and bucket
    repository = PostgresNewsRepository(database_url)
    repository.migrate(Path(__file__).parent.parent / "migrations" / "001_news.sql")
    return NewsIngestionService(repository, MinioEvidenceStore(endpoint, access_key, secret_key, bucket))


ingestion_service = build_ingestion_service()
fake_analyzer = FakeFinancialNewsAnalyzer()
candidate_catalog: dict[str, NewsEventCandidate] = {}

@app.get("/live")
def live() -> dict[str, str]:
    return {"status": "UP"}

@app.get("/ready")
def ready() -> dict[str, object]:
    return {"status": "UP", "dependencies": {}}

@app.get("/metrics")
def metrics() -> str:
    return ""

@app.get("/version")
def version() -> dict[str, str]:
    return {"service": "news-intelligence-service", "version": "0.1.0"}


@app.post("/internal/v1/jobs/collect")
def collect_fixture(item: FixtureNewsInput) -> dict[str, object]:
    try:
        result = ingestion_service.ingest_fixture(item)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"newsItem": result.item, "duplicate": result.duplicate}


@app.post("/internal/v1/news/candidates")
def create_candidate(item: dict[str, object]) -> dict[str, object]:
    """从已采集 NewsItem 和 Security Master Fixture 构建候选事件。"""
    from src.news_ingestion import NewsItem

    try:
        news_item = NewsItem.model_validate(item["newsItem"])
        raw_entities = cast(list[Any], item.get("entities", []))
        entities = tuple(SecurityEntity.model_validate(value) for value in raw_entities)
        candidate = build_candidate(news_item, entities)
    except (KeyError, TypeError, ValueError) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    candidate_catalog[candidate.candidate_id] = candidate
    return {"candidate": candidate}


@app.post("/internal/v1/news/events/analyze")
def analyze_candidate(payload: dict[str, object]) -> dict[str, object]:
    try:
        candidate = NewsEventCandidate.model_validate(payload["candidate"])
        agent_run_id = str(payload["agentRunId"])
        if not agent_run_id:
            raise ValueError("agentRunId must not be empty")
        event = fake_analyzer.analyze(candidate, agent_run_id)
    except (KeyError, TypeError, ValueError) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"event": event, "idempotent": event.agent_run_id == agent_run_id}


@app.get("/api/v1/events")
def list_events() -> dict[str, object]:
    return {"events": fake_analyzer.list()}


@app.get("/api/v1/events/{event_id}")
def get_event(event_id: str) -> dict[str, object]:
    event = fake_analyzer.get(event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="event not found")
    return {"event": event}


@app.get("/api/v1/news/{news_id}/freshness")
def news_freshness(news_id: str, available_at: str, now: str) -> dict[str, str]:
    from datetime import datetime

    try:
        status = freshness_for(datetime.fromisoformat(available_at), datetime.fromisoformat(now))
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"newsId": news_id, "freshness": status}
