import { readFile } from 'node:fs/promises';
import { Pool } from 'pg';
import { afterAll, beforeAll, describe, expect, it } from 'vitest';
import { PostgresProposalRepository } from '../../src/infrastructure/postgres-proposal-repository.js';

const databaseUrl = process.env.DECISION_GOVERNANCE_DATABASE_URL;
const suite = databaseUrl ? describe : describe.skip;
suite('Governance Proposal PostgreSQL persistence', () => {
  const pool = new Pool({ connectionString: databaseUrl }); const proposalId = `integration-${Date.now()}`;
  beforeAll(async () => { await pool.query(await readFile(new URL('../../migrations/001_proposals.sql', import.meta.url), 'utf8')); });
  afterAll(async () => { await pool.query('DELETE FROM trade_proposals WHERE proposal_id = $1', [proposalId]); await pool.end(); });
  it('persists immutable payload and reads latest version', async () => {
    const repository = new PostgresProposalRepository(pool); const proposal = { proposalId, proposalVersion: 1, kind: 'HOLD' as const, state: 'DRAFT' as const, agentRunId: 'run', targetPortfolioVersion: 1, legs: [], evidence: [], contentHash: 'b'.repeat(64), createdAt: '2026-09-04T00:00:00Z' };
    await repository.append({ ...proposal, idempotencyKey: `${proposalId}-key` }, proposal);
    await expect(repository.latest(proposalId)).resolves.toEqual(proposal);
    await expect(repository.findByIdempotency(`${proposalId}-key`)).resolves.toEqual(proposal);
  });
});
