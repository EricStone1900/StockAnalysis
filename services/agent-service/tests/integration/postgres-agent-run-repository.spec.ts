import { readFile } from 'node:fs/promises';
import { Pool } from 'pg';
import { afterAll, describe, expect, it } from 'vitest';
import { PostgresAgentRunRepository } from '../../src/infrastructure/postgres-agent-run-repository.js';

const databaseUrl = process.env.AGENT_DATABASE_URL;
const pool = databaseUrl ? new Pool({ connectionString: databaseUrl }) : undefined;
afterAll(async () => { await pool?.end(); });

describe.skipIf(!pool)('PostgresAgentRunRepository integration', () => {
  it('persists and restores a completed run by correlation id', async () => {
    await pool?.query(await readFile(new URL('../../migrations/001_agent_runs.sql', import.meta.url), 'utf8'));
    const repository = new PostgresAgentRunRepository(pool!);
    const correlationId = `integration-${crypto.randomUUID()}`;
    const run = { runId: `run-${correlationId}`, definitionId: 'fake:v1', correlationId, modelRun: { provider: 'fake', modelId: 'fake', promptVersion: 'p1' }, toolCalls: [], output: { summary: 'ok' } };
    await repository.save(run);
    await repository.save(run);
    expect(await repository.get(correlationId)).toEqual(run);
  });
});
