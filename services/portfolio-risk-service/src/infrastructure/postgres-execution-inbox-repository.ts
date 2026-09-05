import type { Pool } from 'pg';

export class PostgresExecutionInboxRepository {
  constructor(private readonly pool: Pick<Pool, 'query'>) {}
  async accept(event: { eventId: string; subject: string }): Promise<boolean> {
    const result = await this.pool.query<{ event_id: string }>('INSERT INTO portfolio_execution_inbox (event_id, subject) VALUES ($1, $2) ON CONFLICT (event_id) DO NOTHING RETURNING event_id', [event.eventId, event.subject]);
    return result.rows.length === 1;
  }
  async release(eventId: string): Promise<void> {
    await this.pool.query('DELETE FROM portfolio_execution_inbox WHERE event_id = $1', [eventId]);
  }
}
