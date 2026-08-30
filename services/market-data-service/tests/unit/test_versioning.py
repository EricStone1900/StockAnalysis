from datetime import UTC, datetime

from market_data.quality import QualityStatus
from market_data.versioning import DataVersion, DataVersionStatus, VersionRegistry


def candidate(version_id: str, quality: QualityStatus = QualityStatus.PASS, artifact_hash: str = "a" * 64) -> DataVersion:
    return DataVersion(version_id=version_id, scope="CN_A", source_version="fixture-1", artifact_uri="minio://artifacts/test.parquet", artifact_hash=artifact_hash, quality_status=quality, available_at=datetime(2026, 8, 28, tzinfo=UTC), content_hash="b" * 64)


def test_failed_candidate_preserves_old_ready_version() -> None:
    registry = VersionRegistry()
    assert registry.publish(candidate("v1"), "first").status is DataVersionStatus.READY
    assert registry.publish(candidate("v2", QualityStatus.FAIL), "second").status is DataVersionStatus.FAILED
    assert registry.latest_ready() is not None and registry.latest_ready().version_id == "v1"


def test_publish_is_idempotent_and_emits_one_event() -> None:
    registry = VersionRegistry()
    assert registry.publish(candidate("v1"), "same") == registry.publish(candidate("v2"), "same")
    assert len(registry.events) == 1


def test_invalid_artifact_hash_blocks_ready() -> None:
    assert VersionRegistry().publish(candidate("v1", artifact_hash="bad"), "key").status is DataVersionStatus.FAILED
