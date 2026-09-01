import os
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from quant_research.daily_analysis import (
    DailyAnalysisInput,
    DailyAnalysisSnapshot,
    DailyCandidateAnalysis,
    DailyQualitySummary,
    DataQualityStatus,
    PostgresDailyAnalysisRepository,
)

pytestmark = pytest.mark.skipif("MARKET_DATA_DATABASE_URL" not in os.environ, reason="requires local PostgreSQL")


def test_postgres_daily_snapshot_is_idempotent() -> None:
    repository = PostgresDailyAnalysisRepository(os.environ["MARKET_DATA_DATABASE_URL"])
    repository.migrate(str(Path(__file__).parents[2] / "migrations/003_daily_analysis.sql"))
    snapshot = DailyAnalysisSnapshot(
        snapshot_id="integration-daily-snapshot", run_id="run", as_of_date=date(2026, 9, 1),
        input=DailyAnalysisInput(data_version_id="dv", universe_version="u", factor_set_version="f", model_version="m", quality_status=DataQualityStatus.WARN),
        candidates=(DailyCandidateAnalysis(security_id="sz.000001", rank=1, score=Decimal(1)),), holdings=(),
        quality=DailyQualitySummary(status=DataQualityStatus.WARN, excluded_count=0), canonical_content_hash="a" * 64,
    )
    repository.publish_atomically(snapshot)
    repository.publish_atomically(snapshot)
    assert repository.get(snapshot.snapshot_id) == snapshot
