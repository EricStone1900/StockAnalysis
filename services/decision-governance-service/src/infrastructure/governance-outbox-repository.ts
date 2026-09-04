import type { GovernanceEvent } from '../domain/governance-events.js';
import type { SqlClient } from './postgres-proposal-repository.js';
export interface GovernanceOutboxRecord { readonly eventId: string; readonly subject: string; readonly aggregateId: string; readonly payload: Record<string, unknown>; readonly availableAt: string; }

export class GovernanceOutboxRepository {
  public constructor(private readonly client: SqlClient) {}
  public async append(event: GovernanceEvent, aggregateId: string): Promise<void> { await this.client.query('INSERT INTO governance_outbox_events (event_id, subject, aggregate_id, payload, available_at) VALUES ($1,$2,$3,$4::jsonb,$5) ON CONFLICT (event_id) DO NOTHING', [event.eventId, event.subject, aggregateId, JSON.stringify(event), event.availableAt]); }
  public async markPublished(eventId: string): Promise<void> { await this.client.query('UPDATE governance_outbox_events SET published_at = now() WHERE event_id = $1 AND published_at IS NULL', [eventId]); }
  public async claim(limit = 50): Promise<readonly GovernanceOutboxRecord[]> { if (!Number.isInteger(limit) || limit < 1 || limit > 500) throw new Error('invalid outbox batch size'); const result = await this.client.query<{ event_id: string; subject: string; aggregate_id: string; payload: Record<string, unknown>; available_at: string }>(`UPDATE governance_outbox_events SET available_at = now() + interval '30 seconds' WHERE ctid IN (SELECT ctid FROM governance_outbox_events WHERE published_at IS NULL AND available_at <= now() ORDER BY created_at FOR UPDATE SKIP LOCKED LIMIT $1) RETURNING event_id, subject, aggregate_id, payload, available_at`, [limit]); return result.rows.map((row) => ({ eventId: row.event_id, subject: row.subject, aggregateId: row.aggregate_id, payload: row.payload, availableAt: row.available_at })); }
}
