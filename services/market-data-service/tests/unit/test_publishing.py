import asyncio
import json
from datetime import UTC, datetime

from market_data.outbox import InMemoryOutbox
from market_data.publishing import DataVersionPublisher
from market_data.quality import QualityStatus
from market_data.storage import ArtifactStore
from market_data.versioning import DataVersion, DataVersionStatus, VersionRegistry


def candidate(version_id: str, quality: QualityStatus = QualityStatus.PASS) -> DataVersion:
    return DataVersion(
        version_id=version_id,
        scope="CN_A",
        source_version="fixture-1",
        artifact_uri="minio://artifacts/test.parquet",
        artifact_hash="a" * 64,
        quality_status=quality,
        available_at=datetime(2026, 8, 28, tzinfo=UTC),
        content_hash="b" * 64,
    )


def publisher(published: list[tuple[str, bytes]], verify_error: bool = False) -> DataVersionPublisher:
    store = ArtifactStore("http://unused", "key", "secret", "artifacts")

    def get_verified(_: str, __: str) -> bytes:
        if verify_error:
            raise ValueError("artifact hash mismatch")
        return b"artifact"

    store.get_verified = get_verified  # type: ignore[method-assign]

    async def publish(subject: str, payload: bytes) -> None:
        published.append((subject, payload))

    return DataVersionPublisher(VersionRegistry(), store, publish, InMemoryOutbox())


def test_publish_verifies_artifact_and_emits_contract_event() -> None:
    published: list[tuple[str, bytes]] = []
    service = publisher(published)
    result = asyncio.run(service.publish(candidate("v1"), "request-1"))

    assert result.status is DataVersionStatus.READY
    assert len(published) == 1
    subject, payload = published[0]
    assert subject == "stock.market-data.data-version.published.v1"
    assert json.loads(payload) == {
        "subject": subject,
        "versionId": "v1",
        "scope": "CN_A",
        "qualityStatus": "PASS",
        "artifactUri": "minio://artifacts/test.parquet",
        "occurredAt": "2026-08-28T00:00:00+00:00",
    }


def test_publish_is_idempotent_and_does_not_duplicate_outbox_event() -> None:
    published: list[tuple[str, bytes]] = []
    service = publisher(published)
    assert asyncio.run(service.publish(candidate("v1"), "same")).status is DataVersionStatus.READY
    assert asyncio.run(service.publish(candidate("v2"), "same")).version_id == "v1"
    assert len(published) == 1


def test_bad_artifact_and_quality_failure_never_become_ready() -> None:
    published: list[tuple[str, bytes]] = []
    assert asyncio.run(publisher(published, verify_error=True).publish(candidate("bad"), "bad")).status is DataVersionStatus.FAILED
    assert asyncio.run(publisher(published).publish(candidate("failed", QualityStatus.FAIL), "failed")).status is DataVersionStatus.FAILED
    assert published == []
