import { describe, expect, it } from 'vitest';
import { PostgresAgentRunRepository } from '../../src/infrastructure/postgres-agent-run-repository.js';

describe('PostgresAgentRunRepository', () => {
  it('uses correlation id as the durable idempotency key', async () => {
    const calls: string[] = [];
    const repository = new PostgresAgentRunRepository({ query: async (sql) => { calls.push(sql); return { rows: [] }; } });
    await repository.save({ runId: 'run-1', definitionId: 'fake:v1', correlationId: 'corr-1', modelRun: { provider: 'fake', modelId: 'fake', promptVersion: 'p1' }, toolCalls: [], output: { summary: 'ok' } });
    expect(calls[0]).toContain('ON CONFLICT (correlation_id) DO NOTHING');
  });
});
