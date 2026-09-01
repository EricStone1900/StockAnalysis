import os

from fastapi import FastAPI, HTTPException

from quant_research.daily_analysis import (
    InMemoryDailyAnalysisRepository,
    PostgresDailyAnalysisRepository,
)
from quant_research.metadata_repository import (
    InMemoryResearchMetadataRepository,
    PostgresResearchMetadataRepository,
    ResearchMetadataRepository,
)
from quant_research.strategy import (
    InMemoryStrategyRegistry,
    InMemoryStrategySnapshotRepository,
    StrategyRunService,
)


def _metadata_repository() -> ResearchMetadataRepository:
    database_url = os.getenv("QUANT_RESEARCH_DATABASE_URL")
    if database_url:
        return PostgresResearchMetadataRepository(database_url)
    return InMemoryResearchMetadataRepository()

app = FastAPI(title="quant-research-service", version="0.1.0")
metadata_repository = _metadata_repository()
strategy_registry = InMemoryStrategyRegistry()
strategy_snapshot_repository = InMemoryStrategySnapshotRepository()
strategy_run_service = StrategyRunService(strategy_snapshot_repository)
_daily_database_url = os.getenv("QUANT_RESEARCH_DATABASE_URL")
daily_analysis_repository = (
    PostgresDailyAnalysisRepository(_daily_database_url)
    if _daily_database_url
    else InMemoryDailyAnalysisRepository()
)


@app.get("/live")
def live() -> dict[str, str]:
    return {"status": "UP"}


@app.get("/ready")
def ready() -> dict[str, object]:
    return {
        "status": "UP",
        "dependencies": {},
        "capabilities": {
            "qlib_adapter": "S6_ARTIFACT_MATERIALIZER",
            "close_gap_handling": "S0_CONTRACT_FROZEN",
            "metadata_query": "S3_POSTGRES_OR_IN_MEMORY",
        },
    }


@app.get("/metrics")
def metrics() -> str:
    return ""


@app.get("/version")
def version() -> dict[str, str]:
    return {"service": "quant-research-service", "version": "0.1.0"}


@app.get("/api/v1/runs/{run_id}")
def get_training_run(run_id: str) -> object:
    result = metadata_repository.get_training_run(run_id)
    if result is None:
        raise HTTPException(status_code=404, detail="training run not found")
    return result


@app.get("/api/v1/daily-analysis-snapshots/{snapshot_id}")
def get_daily_analysis_snapshot(snapshot_id: str) -> object:
    result = daily_analysis_repository.get(snapshot_id)
    if result is None:
        raise HTTPException(status_code=404, detail="daily analysis snapshot not found")
    return result


@app.get("/api/v1/evaluations/{report_id}")
def get_evaluation_report(report_id: str) -> object:
    result = metadata_repository.get_evaluation_report(report_id)
    if result is None:
        raise HTTPException(status_code=404, detail="evaluation report not found")
    return result


@app.get("/api/v1/backtests/{run_id}")
def get_backtest_report(run_id: str) -> object:
    result = metadata_repository.get_backtest_report(run_id)
    if result is None:
        raise HTTPException(status_code=404, detail="backtest report not found")
    return result


@app.get("/api/v1/strategies/{strategy_id}/{version}")
def get_strategy_version(strategy_id: str, version: str) -> object:
    result = strategy_registry.get(strategy_id, version)
    if result is None:
        raise HTTPException(status_code=404, detail="strategy version not found")
    return result


@app.get("/api/v1/strategy-snapshots/{snapshot_id}")
def get_strategy_snapshot(snapshot_id: str) -> object:
    result = strategy_snapshot_repository.get(snapshot_id)
    if result is None:
        raise HTTPException(status_code=404, detail="strategy snapshot not found")
    return result


@app.get("/api/v1/strategy-runs/{run_id}")
def get_strategy_run(run_id: str) -> object:
    result = strategy_run_service.get(run_id)
    if result is None:
        raise HTTPException(status_code=404, detail="strategy run not found")
    return result
