from fastapi import FastAPI, HTTPException

from src.news_ingestion import (
    FixtureNewsInput,
    InMemoryArtifactStore,
    InMemoryNewsRepository,
    NewsIngestionService,
)

app = FastAPI(title="news-intelligence-service", version="0.1.0")
ingestion_service = NewsIngestionService(InMemoryNewsRepository(), InMemoryArtifactStore())

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
