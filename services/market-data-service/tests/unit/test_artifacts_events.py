from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from market_data.artifacts import write_qlib_view
from market_data.domain import Exchange, SecurityId
from market_data.events import Inbox
from market_data.pit import DailyBar, RawArtifact


def test_qlib_view_is_immutable_parquet(tmp_path: Path) -> None:
    artifact = RawArtifact(
        source="fixture",
        source_record_id="r",
        source_version="fixture-1",
        raw_artifact_uri="minio://artifacts/fixtures/r.json",
        raw_artifact_hash="a" * 64,
        license_ref="test-only",
        source_policy_version="fixture-v1",
        ingested_at=datetime.now(UTC),
    )
    bar = DailyBar(security_id=SecurityId(exchange=Exchange.SSE, symbol="600000"), trading_day=date(2026, 8, 28), open=Decimal(1), high=Decimal(1), low=Decimal(1), close=Decimal(1), volume=Decimal(1), amount=Decimal(1), available_at=datetime.now(UTC), artifact=artifact)
    first_target = tmp_path / "v1.parquet"
    second_target = tmp_path / "v1-rebuild.parquet"
    first_hash = write_qlib_view([bar], first_target)
    second_hash = write_qlib_view([bar], second_target)
    assert len(first_hash) == 64
    assert first_hash == second_hash
    assert first_target.exists()


def test_inbox_event_is_idempotent() -> None:
    inbox = Inbox()
    event_id = uuid4()
    assert inbox.consume_once(event_id, "quant-research")
    assert not inbox.consume_once(event_id, "quant-research")
