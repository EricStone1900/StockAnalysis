import { describe, expect, it, vi } from 'vitest';
import { PostgresPortfolioRepository } from '../../src/infrastructure/postgres-portfolio-repository.js';

const snapshot = { snapshotId: 's-1', portfolioId: 'p-1', accountId: 'a-1', asOf: '2026-09-03T00:00:00Z', cash: '1', positions: [], ledgerVersion: 1, sourceRef: 'src', contentHash: 'hash' } as const;
const command = { portfolioId: 'p-1', accountId: 'a-1', cash: '1', positions: [], occurredAt: snapshot.asOf, availableAt: snapshot.asOf, sourceRef: 'src', actorId: 'actor', reason: 'opening', expectedVersion: 0, idempotencyKey: 'key-1' } as const;

describe('PostgresPortfolioRepository', () => {
  it('uses parameterized queries and persists the immutable payload', async () => {
    const query = vi.fn().mockResolvedValue({ rows: [] });
    await new PostgresPortfolioRepository({ query }).appendOpening(command, snapshot);
    expect(query).toHaveBeenCalledTimes(5);
    expect(query.mock.calls.every(([sql]) => !String(sql).includes('p-1'))).toBe(true);
  });

  it('reads the latest snapshot and idempotency record', async () => {
    const query = vi.fn().mockResolvedValue({ rows: [{ payload: snapshot }] });
    const repository = new PostgresPortfolioRepository({ query });
    await expect(repository.latest('p-1')).resolves.toEqual(snapshot);
    await expect(repository.findByIdempotency('p-1', 'key-1')).resolves.toEqual(snapshot);
  });

  it('persists a reversal linked to its original entry', async () => {
    const query = vi.fn().mockResolvedValue({ rows: [] });
    await new PostgresPortfolioRepository({ query }).appendReversal({ portfolioId: 'p-1', originalEntryId: 'entry-1', occurredAt: '2026-09-03T00:00:00Z', availableAt: '2026-09-03T00:00:00Z', sourceRef: 'reversal', actorId: 'actor', reason: '冲正', expectedVersion: 1, idempotencyKey: 'key' }, { entryId: 'reversal-1', portfolioId: 'p-1', type: 'REVERSAL', amount: '-1', occurredAt: '2026-09-03T00:00:00Z', availableAt: '2026-09-03T00:00:00Z', sourceRef: 'reversal', actorId: 'actor', reason: '冲正' });
    expect(query).toHaveBeenCalledWith(expect.stringContaining('reversal_of_entry_id'), expect.arrayContaining(['entry-1']));
  });
});
