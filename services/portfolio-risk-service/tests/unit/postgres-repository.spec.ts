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

  it('reads an original ledger entry for restart recovery', async () => {
    const query = vi.fn().mockResolvedValue({ rows: [{ entry_id: 'entry-1', portfolio_id: 'p-1', entry_type: 'OPENING', amount: '1', occurred_at: '2026-09-03T00:00:00Z', available_at: '2026-09-03T00:00:00Z', source_ref: 'src', actor_id: 'actor', reason: 'opening' }] });
    await expect(new PostgresPortfolioRepository({ query }).findEntry('entry-1')).resolves.toMatchObject({ entryId: 'entry-1', type: 'OPENING' });
  });

  it('persists risk evaluations idempotently by proposal and policy version', async () => {
    const query = vi.fn().mockResolvedValueOnce({ rows: [] }).mockResolvedValueOnce({ rows: [{ evaluation_id: 'risk-1' }] }).mockResolvedValue({ rows: [] });
    await new PostgresPortfolioRepository({ query }).appendRiskEvaluation({ evaluationId: 'risk-1', proposalId: 'proposal-1', policyVersion: 'policy-v1', verdict: 'PASS', rules: [], before: { cash: '1', totalEquity: '1' }, projectedAfter: { cash: '1', totalEquity: '1' } }, 'p-1');
    expect(query.mock.calls.some(([sql]) => String(sql).includes('portfolio_risk_evaluations'))).toBe(true);
    expect(query.mock.calls.some(([sql]) => String(sql).includes('portfolio_outbox_events'))).toBe(true);
  });

  it('claims pending outbox events with a bounded batch and marks them published', async () => {
    const query = vi.fn().mockResolvedValueOnce({ rows: [{ event_id: 'event-1', subject: 'stock.portfolio-risk.risk-evaluation.created.v1', aggregate_id: 'p-1', payload: { evaluation: {} }, available_at: '2026-09-04T00:00:00Z' }] }).mockResolvedValue({ rows: [] });
    const repository = new PostgresPortfolioRepository({ query });
    await expect(repository.claimOutboxEvents(10)).resolves.toEqual([{ eventId: 'event-1', subject: 'stock.portfolio-risk.risk-evaluation.created.v1', aggregateId: 'p-1', payload: { evaluation: {} }, availableAt: '2026-09-04T00:00:00Z' }]);
    await repository.markOutboxPublished('event-1');
    expect(query).toHaveBeenLastCalledWith(expect.stringContaining('published_at = now()'), ['event-1']);
  });
});
