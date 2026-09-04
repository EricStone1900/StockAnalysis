import type { GovernanceEvent } from '../domain/governance-events.js';
import type { SqlClient } from './postgres-proposal-repository.js';

export class GovernanceOutboxRepository {
  public constructor(private readonly client: SqlClient) {}
  public async append(event: GovernanceEvent, aggregateId: string): Promise<void> { await this.client.query('INSERT INTO governance_outbox_events (event_id, subject, aggregate_id, payload, available_at) VALUES ($1,$2,$3,$4::jsonb,$5) ON CONFLICT (event_id) DO NOTHING', [event.eventId, event.subject, aggregateId, JSON.stringify(event), event.availableAt]); }
  public async markPublished(eventId: string): Promise<void> { await this.client.query('UPDATE governance_outbox_events SET published_at = now() WHERE event_id = $1 AND published_at IS NULL', [eventId]); }
}
