from datetime import datetime
from uuid import UUID


class Inbox:
    def __init__(self) -> None: self._handled: set[tuple[UUID, str]] = set()
    def consume_once(self, event_id: UUID, consumer: str) -> bool:
        key = (event_id, consumer)
        if key in self._handled: return False
        self._handled.add(key)
        return True


def data_version_event(
    version_id: str,
    scope: str,
    quality_status: str,
    artifact_uri: str,
    occurred_at: datetime,
) -> dict[str, str]:
    return {
        "subject": "stock.market-data.data-version.published.v1",
        "versionId": version_id,
        "scope": scope,
        "qualityStatus": quality_status,
        "artifactUri": artifact_uri,
        "occurredAt": occurred_at.isoformat(),
    }
