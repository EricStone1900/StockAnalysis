# Generated from schemas/domain-event-envelope.schema.json. Do not edit.
from typing import Any
from pydantic import BaseModel

class DomainEventEnvelope(BaseModel):
    eventId: str
    subject: str
    schemaVersion: int
    occurredAt: str
    availableAt: str
    producer: str
    correlationId: str
    causationId: str | None = None
    aggregateId: str | None = None
    aggregateVersion: int | None = None
    payload: dict[str, Any]
