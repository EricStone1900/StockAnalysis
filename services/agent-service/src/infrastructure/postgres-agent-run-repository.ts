import type { AgentRun } from '../application/agent-kernel.js';
import type { AgentRunRepository } from '../application/agent-run-repository.js';

export interface SqlClient { query<T extends Record<string, unknown> = Record<string, unknown>>(sql: string, parameters?: readonly unknown[]): Promise<{ rows: T[] }>; }

export class PostgresAgentRunRepository implements AgentRunRepository {
  public constructor(private readonly client: SqlClient) {}
  public async get(correlationId: string): Promise<AgentRun<unknown> | undefined> {
    const result = await this.client.query<{ payload: AgentRun<unknown> }>('SELECT payload FROM agent_runs WHERE correlation_id = $1', [correlationId]);
    return result.rows[0]?.payload;
  }
  public async save(run: AgentRun<unknown>): Promise<void> {
    await this.client.query('INSERT INTO agent_runs (correlation_id, run_id, definition_id, payload) VALUES ($1,$2,$3,$4::jsonb) ON CONFLICT (correlation_id) DO NOTHING', [run.correlationId, run.runId, run.definitionId, JSON.stringify(run)]);
  }
}
