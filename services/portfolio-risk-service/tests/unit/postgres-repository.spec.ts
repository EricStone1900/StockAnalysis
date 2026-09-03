import { describe, expect, it, vi } from 'vitest';
import { PostgresPortfolioRepository } from '../../src/infrastructure/postgres-portfolio-repository.js';

const snapshot = { snapshotId: 's-1', portfolioId: 'p-1', accountId: 'a-1', asOf: '2026-09-03T00:00:00Z', cash: '1', positions: [], ledgerVersion: 1, sourceRef: 'src', contentHash: 'hash' } as const;
const command = { portfolioId: 'p-1', accountId: 'a-1', cash: '1', positions: [], occurredAt: snapshot.asOf, availableAt: snapshot.asOf, sourceRef: 'src', actorId: 'actor', reason: 'opening', expectedVersion: 0, idempotencyKey: 'key-1' } as const;

describe('PostgresPortfolioRepository', () => {
  it('uses parameterized queries and persists the immutable payload', async () => {
    const query = vi.fn().mockResolvedValue({ rows: [] });
    await new PostgresPortfolioRepository({ query }).appendOpening(command, snapshot);
    expect(query).toHaveBeenCalledTimes(3);
    expect(query.mock.calls.every(([sql]) => !String(sql).includes('p-1'))).toBe(true);
  });

  it('reads the latest snapshot and idempotency record', async () => {
    const query = vi.fn().mockResolvedValue({ rows: [{ payload: snapshot }] });
    const repository = new PostgresPortfolioRepository({ query });
    await expect(repository.latest('p-1')).resolves.toEqual(snapshot);
    await expect(repository.findByIdempotency('p-1', 'key-1')).resolves.toEqual(snapshot);
  });
});
