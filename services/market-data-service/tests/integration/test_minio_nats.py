import asyncio
from datetime import UTC, datetime
from uuid import uuid4

import nats

from market_data.events import Inbox
from market_data.nats_publisher import nats_jetstream_publisher
from market_data.publishing import DataVersionPublisher
from market_data.quality import QualityStatus
from market_data.storage import ArtifactStore
from market_data.versioning import DataVersion, DataVersionStatus, VersionRegistry


def test_minio_artifact_round_trip_and_hash_validation() -> None:
    store = ArtifactStore("http://localhost:9000", "minioadmin", "local-minio-password", "artifacts")
    key = f"integration/{uuid4()}.bin"
    digest = store.put_immutable(key, b"stage-02-artifact")
    assert store.get_verified(key, digest) == b"stage-02-artifact"


def test_nats_jetstream_publish_and_inbox_deduplication() -> None:
    async def publish() -> None:
        client = await nats.connect("nats://localhost:4222")
        await client.jetstream().publish("stock.market-data.data-version.published.v1", b'{"versionId":"test"}')
        await client.drain()
    asyncio.run(publish())
    inbox = Inbox()
    event_id = uuid4()
    assert inbox.consume_once(event_id, "integration-consumer")
    assert not inbox.consume_once(event_id, "integration-consumer")


def test_data_version_publishes_verified_minio_artifact_to_jetstream() -> None:
    store = ArtifactStore("http://localhost:9000", "minioadmin", "local-minio-password", "artifacts")
    key = f"integration/{uuid4()}.parquet"
    digest = store.put_immutable(key, b"verified-stage-02-artifact")
    version = DataVersion(
        version_id=str(uuid4()),
        scope="CN_A",
        source_version="fixture-1",
        artifact_uri=f"minio://artifacts/{key}",
        artifact_hash=digest,
        quality_status=QualityStatus.PASS,
        available_at=datetime.now(UTC),
        content_hash=digest,
    )

    publisher = DataVersionPublisher(VersionRegistry(), store, nats_jetstream_publisher("nats://localhost:4222"))
    result = asyncio.run(publisher.publish(version, "integration-request"))

    assert result.status is DataVersionStatus.READY
    assert len(publisher.outbox.messages) == 1
    assert publisher.outbox.messages[0].delivered
