from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel

from .quality import QualityStatus


class DataVersionStatus(StrEnum):
    BUILDING = "BUILDING"
    VALIDATING = "VALIDATING"
    READY = "READY"
    FAILED = "FAILED"
    SUPERSEDED = "SUPERSEDED"


class DataVersion(BaseModel):
    version_id: str
    status: DataVersionStatus = DataVersionStatus.BUILDING
    scope: str
    source_version: str
    source_release_tag: str | None = None
    source_policy_version: str = "fixture-v1"
    source_manifest_hash: str | None = None
    artifact_uri: str
    artifact_hash: str
    quality_report_uri: str | None = None
    close_gap_index_uri: str | None = None
    close_gap_index_hash: str | None = None
    quality_status: QualityStatus
    available_at: datetime
    content_hash: str
    parent_version_id: str | None = None


class VersionRegistry:
    def __init__(self) -> None:
        self._versions: dict[str, DataVersion] = {}
        self._idempotency: dict[str, DataVersion] = {}
        self.events: list[dict[str, str]] = []

    def publish(self, candidate: DataVersion, idempotency_key: str) -> DataVersion:
        if idempotency_key in self._idempotency:
            return self._idempotency[idempotency_key]
        if candidate.quality_status is QualityStatus.FAIL or len(candidate.artifact_hash) != 64:
            failed = candidate.model_copy(update={"status": DataVersionStatus.FAILED})
            self._versions[failed.version_id] = failed
            self._idempotency[idempotency_key] = failed
            return failed
        for version_id, version in list(self._versions.items()):
            if version.status is DataVersionStatus.READY:
                self._versions[version_id] = version.model_copy(update={"status": DataVersionStatus.SUPERSEDED})
        ready = candidate.model_copy(update={"status": DataVersionStatus.READY})
        self._versions[ready.version_id] = ready
        self._idempotency[idempotency_key] = ready
        self.events.append({"subject": "stock.market-data.data-version.published.v1", "versionId": ready.version_id, "artifactUri": ready.artifact_uri})
        return ready

    def latest_ready(self) -> DataVersion | None:
        return next((version for version in reversed(list(self._versions.values())) if version.status is DataVersionStatus.READY), None)
