from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from quant_research.daily_analysis import (
    DailyAnalysisEventPublisher,
    DailyAnalysisInput,
    DailyAnalysisService,
    DailyCandidateAnalysis,
    DailyHoldingAnalysis,
    DailyQualitySummary,
    DataQualityStatus,
    InMemoryDailyAnalysisRepository,
)


class Events:
    def __init__(self) -> None:
        self.items: list[tuple[str, dict[str, object]]] = []

    def publish(self, subject: str, payload: dict[str, object]) -> None:
        self.items.append((subject, payload))


def _input() -> DailyAnalysisInput:
    return DailyAnalysisInput(
        data_version_id="dv-1", universe_version="u-1", factor_set_version="f-1",
        model_version="m-1", quality_status=DataQualityStatus.WARN,
    )


def test_daily_analysis_is_idempotent_and_publishes_sorted_snapshot() -> None:
    repo = InMemoryDailyAnalysisRepository()
    events = Events()
    service = DailyAnalysisService(repo, events)
    now = datetime(2026, 9, 1, 1, 0, tzinfo=UTC)
    service.start("run-1", date(2026, 8, 31), _input(), now)
    snapshot = service.publish(
        "run-1",
        (DailyCandidateAnalysis(security_id="sz.000002", rank=2, score=Decimal("1.0")),
         DailyCandidateAnalysis(security_id="sz.000001", rank=1, score=Decimal("2.0"))),
        (DailyHoldingAnalysis(security_id="sz.000001", target_weight=Decimal(1), in_candidate_universe=True),),
        DailyQualitySummary(status=DataQualityStatus.WARN, excluded_count=1, warning_reasons=("close_gap",)),
        ("e2", "e1"), now,
    )
    assert [item.security_id for item in snapshot.candidates] == ["sz.000001", "sz.000002"]
    assert snapshot.evidence_ids == ("e1", "e2")
    assert repo.latest_ready() == snapshot
    assert len(events.items) == 1
    assert events.items[0][0] == "stock.quant.daily-analysis.published.v1"

    assert service.start("run-1", date(2026, 8, 31), _input(), now) == service.run("run-1")


def test_duplicate_run_with_different_input_is_rejected() -> None:
    service = DailyAnalysisService(InMemoryDailyAnalysisRepository())
    now = datetime(2026, 9, 1, tzinfo=UTC)
    service.start("run-1", date(2026, 8, 31), _input(), now)
    with pytest.raises(ValueError, match="different input"):
        service.start("run-1", date(2026, 8, 31), _input().model_copy(update={"model_version": "m-2"}), now)


def test_failed_run_keeps_previous_ready_snapshot() -> None:
    repo = InMemoryDailyAnalysisRepository()
    service = DailyAnalysisService(repo)
    now = datetime(2026, 9, 1, tzinfo=UTC)
    service.start("good", date(2026, 8, 30), _input(), now)
    service.publish("good", (), (), DailyQualitySummary(status=DataQualityStatus.WARN, excluded_count=0), (), now)
    previous = repo.latest_ready()
    service.start("bad", date(2026, 8, 31), _input(), now)
    failed = service.fail("bad", "factor calculation failed", now)
    assert failed.failure_reason == "factor calculation failed"
    assert repo.latest_ready() == previous


def test_failed_quality_and_non_utc_timestamps_are_rejected() -> None:
    with pytest.raises(ValueError, match="FAIL input"):
        DailyAnalysisInput(data_version_id="dv", universe_version="u", factor_set_version="f", model_version="m", quality_status=DataQualityStatus.FAIL)
    service = DailyAnalysisService(InMemoryDailyAnalysisRepository())
    with pytest.raises(ValueError, match="UTC"):
        service.start("run", date(2026, 8, 31), _input(), datetime.fromisoformat("2026-09-01T00:00:00"))


def test_event_publisher_protocol_is_structurally_usable() -> None:
    assert DailyAnalysisEventPublisher is not None
