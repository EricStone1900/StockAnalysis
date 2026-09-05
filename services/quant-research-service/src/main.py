import os
from datetime import UTC, datetime
from decimal import Decimal

from fastapi import FastAPI, HTTPException

from quant_research.daily_analysis import (
    DailyAnalysisInput,
    DailyAnalysisService,
    DailyCandidateAnalysis,
    DailyHoldingAnalysis,
    DailyQualitySummary,
    InMemoryDailyAnalysisRepository,
    PostgresDailyAnalysisRepository,
)
from quant_research.domain import DataQualityStatus
from quant_research.metadata_repository import (
    InMemoryResearchMetadataRepository,
    PostgresResearchMetadataRepository,
    ResearchMetadataRepository,
)
from quant_research.strategy import (
    InMemoryStrategyRegistry,
    InMemoryStrategySnapshotRepository,
    PostgresStrategyMetadataRepository,
    StrategyRunService,
)


def _metadata_repository() -> ResearchMetadataRepository:
    database_url = os.getenv("QUANT_RESEARCH_DATABASE_URL")
    if database_url:
        return PostgresResearchMetadataRepository(database_url)
    return InMemoryResearchMetadataRepository()

app = FastAPI(title="quant-research-service", version="0.1.0")
_daily_database_url = os.getenv("QUANT_RESEARCH_DATABASE_URL")
metadata_repository = _metadata_repository()
strategy_registry = InMemoryStrategyRegistry()
strategy_snapshot_repository = InMemoryStrategySnapshotRepository()
_strategy_database_repository = PostgresStrategyMetadataRepository(_daily_database_url) if _daily_database_url else None
strategy_run_service = StrategyRunService(strategy_snapshot_repository)
daily_analysis_repository = (
    PostgresDailyAnalysisRepository(_daily_database_url)
    if _daily_database_url
    else InMemoryDailyAnalysisRepository()
)


def _seed_fast_fixture() -> None:
    """仅供本地验收；默认关闭，避免生产伪造业务快照。"""
    if os.getenv("QUANT_RESEARCH_SEED_FIXTURE") != "1":
        return
    now = datetime.now(UTC)
    as_of_date = now.date()
    run_id = f"local-fast-fixture-{as_of_date.isoformat()}"
    service = DailyAnalysisService(daily_analysis_repository)
    service.start(
        run_id,
        as_of_date,
        DailyAnalysisInput(
            data_version_id="local-fast-data-version",
            universe_version="local-fast-universe-v1",
            factor_set_version="local-fast-factors-v1",
            model_version="local-fast-model-v1",
            quality_status=DataQualityStatus.WARN,
        ),
        now,
    )
    service.publish(
        run_id,
        (DailyCandidateAnalysis(security_id="SSE:600000", rank=1, score=Decimal("0.8"), signals=("FAST_FIXTURE",)),),
        (DailyHoldingAnalysis(security_id="SSE:600000", target_weight=Decimal(0), in_candidate_universe=True, signals=()),),
        DailyQualitySummary(status=DataQualityStatus.WARN, excluded_count=0, warning_reasons=("FAST_LOCAL_FIXTURE",)),
        ("local-fast-data-version", "local-fast-fixture"),
        now,
    )


_seed_fast_fixture()


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


@app.get("/api/v1/daily-analysis-snapshots/latest")
def get_latest_daily_analysis_snapshot() -> object:
    result = daily_analysis_repository.latest_ready()
    if result is None:
        raise HTTPException(status_code=404, detail="latest daily analysis snapshot not found")
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
    result = (_strategy_database_repository.get_version(strategy_id, version) if _strategy_database_repository else strategy_registry.get(strategy_id, version))
    if result is None:
        raise HTTPException(status_code=404, detail="strategy version not found")
    return result


@app.get("/api/v1/strategy-snapshots/{snapshot_id}")
def get_strategy_snapshot(snapshot_id: str) -> object:
    result = (_strategy_database_repository.get_snapshot(snapshot_id) if _strategy_database_repository else strategy_snapshot_repository.get(snapshot_id))
    if result is None:
        raise HTTPException(status_code=404, detail="strategy snapshot not found")
    return result


@app.get("/api/v1/strategy-runs/{run_id}")
def get_strategy_run(run_id: str) -> object:
    result = (_strategy_database_repository.get_run(run_id) if _strategy_database_repository else strategy_run_service.get(run_id))
    if result is None:
        raise HTTPException(status_code=404, detail="strategy run not found")
    return result
