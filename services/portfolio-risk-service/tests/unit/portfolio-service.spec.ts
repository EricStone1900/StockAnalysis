import { describe, expect, it, vi } from 'vitest';
import { PortfolioService } from '../../src/application/portfolio-service.js';
import { PortfolioLedger } from '../../src/domain/portfolio.js';

const command = { portfolioId: 'p-1', accountId: 'a-1', cash: '1', positions: [], occurredAt: '2026-09-03T00:00:00Z', availableAt: '2026-09-03T00:00:00Z', sourceRef: 'src', actorId: 'actor', reason: 'test', expectedVersion: 2, idempotencyKey: 'key' } as const;

describe('PortfolioService database recovery', () => {
  it('restores the latest persisted version before checking expectedVersion', async () => {
    const latest = { ...new PortfolioLedger().importOpening({ ...command, expectedVersion: 0 }), ledgerVersion: 2 };
    const repository = { findByIdempotency: vi.fn().mockResolvedValue(undefined), latest: vi.fn().mockResolvedValue(latest), appendOpening: vi.fn().mockResolvedValue(undefined) };
    const service = new PortfolioService(new PortfolioLedger(), repository);
    const snapshot = await service.importOpening(command);
    expect(snapshot.ledgerVersion).toBe(3);
    expect(repository.appendOpening).toHaveBeenCalledOnce();
  });
});
