"""研究运行、模型评估和回测元数据登记端口。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Protocol, TypeVar

from quant_research.models import EvaluationReport, TrainingRun
from quant_research.portfolio_backtest import PortfolioBacktestReport

T = TypeVar("T", TrainingRun, EvaluationReport, PortfolioBacktestReport)


class MetadataConflictError(ValueError):
    """同一标识已存在但内容不同。"""


class ResearchMetadataRepository(Protocol):
    def save_training_run(self, run: TrainingRun) -> None: ...

    def save_evaluation_report(self, report: EvaluationReport) -> None: ...

    def save_backtest_report(self, run_id: str, report: PortfolioBacktestReport) -> None: ...

    def get_training_run(self, run_id: str) -> TrainingRun | None: ...

    def get_evaluation_report(self, report_id: str) -> EvaluationReport | None: ...

    def get_backtest_report(self, run_id: str) -> PortfolioBacktestReport | None: ...


class InMemoryResearchMetadataRepository:
    """单元测试与本地组件验证使用的幂等登记实现。"""

    def __init__(self) -> None:
        self._records: dict[tuple[str, str], str] = {}

    def save_training_run(self, run: TrainingRun) -> None:
        self._save("training_run", run.run_id, run)

    def save_evaluation_report(self, report: EvaluationReport) -> None:
        self._save("evaluation_report", report.report_id, report)

    def save_backtest_report(self, run_id: str, report: PortfolioBacktestReport) -> None:
        self._save("backtest_report", run_id, report)

    def get_training_run(self, run_id: str) -> TrainingRun | None:
        return self._get("training_run", run_id, TrainingRun)

    def get_evaluation_report(self, report_id: str) -> EvaluationReport | None:
        return self._get("evaluation_report", report_id, EvaluationReport)

    def get_backtest_report(self, run_id: str) -> PortfolioBacktestReport | None:
        return self._get("backtest_report", run_id, PortfolioBacktestReport)

    def _save(self, record_type: str, record_id: str, value: object) -> None:
        payload = _canonical_json(value)
        key = (record_type, record_id)
        if key in self._records and self._records[key] != payload:
            raise MetadataConflictError(f"{record_type} {record_id} already contains different content")
        self._records[key] = payload

    def _get(self, record_type: str, record_id: str, model_type: type[T]) -> T | None:
        payload = self._records.get((record_type, record_id))
        return None if payload is None else model_type.model_validate_json(payload)


class PostgresResearchMetadataRepository:
    """PostgreSQL JSONB登记实现；数据库只保存元数据，不保存大对象内容。"""

    def __init__(self, database_url: str) -> None:
        self._database_url = database_url

    def migrate(self, migration: Path) -> None:
        import psycopg

        with psycopg.connect(self._database_url, autocommit=True) as connection:
            connection.execute(migration.read_text(encoding="utf-8"))

    def save_training_run(self, run: TrainingRun) -> None:
        self._save("training_run", run.run_id, run)

    def save_evaluation_report(self, report: EvaluationReport) -> None:
        self._save("evaluation_report", report.report_id, report)

    def save_backtest_report(self, run_id: str, report: PortfolioBacktestReport) -> None:
        self._save("backtest_report", run_id, report)

    def get_training_run(self, run_id: str) -> TrainingRun | None:
        return self._get("training_run", run_id, TrainingRun)

    def get_evaluation_report(self, report_id: str) -> EvaluationReport | None:
        return self._get("evaluation_report", report_id, EvaluationReport)

    def get_backtest_report(self, run_id: str) -> PortfolioBacktestReport | None:
        return self._get("backtest_report", run_id, PortfolioBacktestReport)

    def _save(self, record_type: str, record_id: str, value: object) -> None:
        import psycopg

        payload = _canonical_json(value)
        with psycopg.connect(self._database_url) as connection:
            row = connection.execute(
                "SELECT payload::text FROM research_metadata_records WHERE record_type = %s AND record_id = %s",
                (record_type, record_id),
            ).fetchone()
            if row is not None:
                existing = json.dumps(json.loads(str(row[0])), ensure_ascii=False, separators=(",", ":"), sort_keys=True)
                if existing != payload:
                    raise MetadataConflictError(f"{record_type} {record_id} already contains different content")
                return
            connection.execute(
                "INSERT INTO research_metadata_records(record_type, record_id, payload) VALUES (%s, %s, %s::jsonb)",
                (record_type, record_id, payload),
            )

    def _get(self, record_type: str, record_id: str, model_type: type[T]) -> T | None:
        import psycopg

        with psycopg.connect(self._database_url) as connection:
            row = connection.execute(
                "SELECT payload::text FROM research_metadata_records WHERE record_type = %s AND record_id = %s",
                (record_type, record_id),
            ).fetchone()
        return None if row is None else model_type.model_validate_json(str(row[0]))


def _canonical_json(value: object) -> str:
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json")
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
