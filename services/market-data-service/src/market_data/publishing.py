import json
from collections.abc import Awaitable, Callable

from .events import data_version_event
from .outbox import InMemoryOutbox, OutboxRelay
from .storage import ArtifactStore
from .versioning import DataVersion, DataVersionStatus, VersionRegistry

DATA_VERSION_SUBJECT = "stock.market-data.data-version.published.v1"


class DataVersionPublisher:
    """协调 Artifact 校验、版本发布与可靠事件投递。"""

    def __init__(
        self,
        registry: VersionRegistry,
        artifact_store: ArtifactStore,
        publish: Callable[[str, bytes], Awaitable[None]],
        outbox: InMemoryOutbox | None = None,
    ) -> None:
        self.registry = registry
        self.artifact_store = artifact_store
        self.outbox = outbox or InMemoryOutbox()
        self.relay = OutboxRelay(publish)

    async def publish(self, candidate: DataVersion, idempotency_key: str) -> DataVersion:
        if candidate.quality_status.value == "FAIL":
            return self.registry.publish(candidate, idempotency_key)
        try:
            self._verify_artifact(candidate)
        except ValueError:
            failed_candidate = candidate.model_copy(update={"artifact_hash": "invalid"})
            return self.registry.publish(failed_candidate, idempotency_key)
        events_before = len(self.registry.events)
        version = self.registry.publish(candidate, idempotency_key)
        if version.status is not DataVersionStatus.READY or len(self.registry.events) == events_before:
            return version

        event = data_version_event(
            version.version_id,
            version.scope,
            version.quality_status.value,
            version.artifact_uri,
            version.available_at,
        )
        payload = json.dumps(event, separators=(",", ":")).encode()
        self.outbox.enqueue(DATA_VERSION_SUBJECT, payload)
        await self.relay.relay_pending(self.outbox)
        return version

    def _verify_artifact(self, candidate: DataVersion) -> None:
        prefix = f"minio://{self.artifact_store.bucket}/"
        if not candidate.artifact_uri.startswith(prefix):
            raise ValueError("artifact URI does not belong to the configured artifact bucket")
        key = candidate.artifact_uri.removeprefix(prefix)
        self.artifact_store.get_verified(key, candidate.artifact_hash)
