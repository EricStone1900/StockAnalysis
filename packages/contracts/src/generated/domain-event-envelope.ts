// Generated from schemas/domain-event-envelope.schema.json. Do not edit.
export interface DomainEventEnvelope {
  eventId: string;
  subject: string;
  schemaVersion: number;
  occurredAt: string;
  availableAt: string;
  producer: string;
  correlationId: string;
  causationId?: string;
  aggregateId?: string;
  aggregateVersion?: number;
  payload: Record<string, unknown>;
}
