import type { ExecutionEvent } from '../domain/execution-events.js'; import type { SqlClient } from './postgres-execution-repository.js'; import type { ExecutionOutboxRecord } from '../application/outbox-worker.js';
export class ExecutionOutboxRepository {
  public constructor(private readonly client: SqlClient) {}
  public async append(event: ExecutionEvent, aggregateId: string): Promise<void> { await this.client.query('INSERT INTO execution_outbox_events (event_id, subject, aggregate_id, payload, available_at) VALUES ($1,$2,$3,$4::jsonb,$5) ON CONFLICT (event_id) DO NOTHING', [event.eventId, event.subject, aggregateId, JSON.stringify(event), event.availableAt]); }
  public async claim(limit = 50): Promise<readonly ExecutionOutboxRecord[]> {
    const result = await this.client.query<Record<string, unknown>>(`WITH candidates AS (SELECT event_id FROM execution_outbox_events WHERE published_at IS NULL AND available_at <= now() AND (claimed_until IS NULL OR claimed_until < now()) ORDER BY available_at, created_at FOR UPDATE SKIP LOCKED LIMIT $1) UPDATE execution_outbox_events e SET claimed_until = now() + interval '30 seconds' FROM candidates c WHERE e.event_id = c.event_id RETURNING e.event_id AS "eventId", e.subject, e.aggregate_id AS "aggregateId", e.payload, e.available_at AS "availableAt"`, [limit]);
    return result.rows as unknown as ExecutionOutboxRecord[];
  }
  public async markPublished(eventId: string): Promise<void> { await this.client.query('UPDATE execution_outbox_events SET published_at = now(), claimed_until = NULL WHERE event_id = $1 AND published_at IS NULL', [eventId]); }
}
