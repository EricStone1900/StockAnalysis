import { readFile } from 'node:fs/promises';
import { Pool } from 'pg';
import { afterAll, beforeAll, describe, expect, it } from 'vitest';
import { PostgresPortfolioRepository } from '../../src/infrastructure/postgres-portfolio-repository.js';
import { PortfolioLedger } from '../../src/domain/portfolio.js';

const databaseUrl = process.env.PORTFOLIO_DATABASE_URL;
const suite = databaseUrl ? describe : describe.skip;

suite('PostgreSQL portfolio persistence', () => {
  const pool = new Pool({ connectionString: databaseUrl, max: 2 });
  const portfolioId = `integration-${Date.now()}`;
  const command = {
    portfolioId, accountId: 'account-integration', cash: '100.00', positions: [{ securityId: 'SSE:600000', quantity: '10' }],
    occurredAt: '2026-09-03T01:00:00Z', availableAt: '2026-09-03T01:00:00Z', sourceRef: 'integration-test', actorId: 'test', reason: '集成测试', expectedVersion: 0, idempotencyKey: 'integration-key',
  } as const;

  beforeAll(async () => {
    await pool.query(await readFile(new URL('../../migrations/001_portfolio_ledger.sql', import.meta.url), 'utf8'));
  });
  afterAll(async () => { await pool.query('DELETE FROM portfolio_snapshot_idempotency WHERE portfolio_id = $1', [portfolioId]); await pool.query('DELETE FROM portfolio_snapshots WHERE portfolio_id = $1', [portfolioId]); await pool.query('DELETE FROM portfolio_ledger_entries WHERE portfolio_id = $1', [portfolioId]); await pool.end(); });

  it('persists and reads an immutable opening snapshot idempotently', async () => {
    const snapshot = new PortfolioLedger().importOpening(command);
    const repository = new PostgresPortfolioRepository(pool);
    await repository.appendOpening(command, snapshot);
    await expect(repository.latest(portfolioId)).resolves.toEqual(snapshot);
    await expect(repository.findByIdempotency(portfolioId, command.idempotencyKey)).resolves.toEqual(snapshot);
  });

  it('rolls back all writes when a later insert fails', async () => {
    const snapshot = new PortfolioLedger().importOpening({ ...command, idempotencyKey: 'rollback-key' });
    const repository = new PostgresPortfolioRepository(pool);
    await expect(repository.appendOpening({ ...command, idempotencyKey: 'integration-key' }, snapshot)).rejects.toThrow();
    const count = await pool.query<{ count: string }>('SELECT count(*)::text AS count FROM portfolio_ledger_entries WHERE entry_id = $1', [`ledger-entry-${snapshot.snapshotId}`]);
    expect(count.rows[0]?.count).toBe('1');
  });
});
