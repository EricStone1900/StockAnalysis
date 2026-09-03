import { describe, expect, it } from 'vitest';
import { PortfolioLedger } from '../../src/domain/portfolio.js';

const command = (overrides: Partial<Parameters<PortfolioLedger['importOpening']>[0]> = {}) => ({
  portfolioId: 'portfolio-1', accountId: 'account-1', cash: '100000.00', positions: [{ securityId: 'SSE:600000', quantity: '100' }],
  occurredAt: '2026-09-03T01:00:00Z', availableAt: '2026-09-03T01:00:00Z', sourceRef: 'manual-import-1', actorId: 'operator-1', reason: '期初导入', expectedVersion: 0, idempotencyKey: 'opening-1', ...overrides,
});

describe('portfolio ledger opening snapshot', () => {
  it('imports an immutable deterministic snapshot', () => {
    const snapshot = new PortfolioLedger().importOpening(command());
    expect(snapshot.ledgerVersion).toBe(1);
    expect(snapshot.positions[0]?.availableQuantity).toBe('100');
    expect(snapshot.contentHash).toHaveLength(64);
  });

  it('is idempotent and rejects stale versions', () => {
    const ledger = new PortfolioLedger();
    const first = ledger.importOpening(command());
    expect(ledger.importOpening(command({ expectedVersion: 99 }))).toEqual(first);
    expect(() => ledger.importOpening(command({ idempotencyKey: 'opening-2', expectedVersion: 0 }))).toThrow('version conflict');
  });

  it('rejects negative quantity and excessive decimal precision', () => {
    const ledger = new PortfolioLedger();
    expect(() => ledger.importOpening(command({ positions: [{ securityId: 'SSE:600000', quantity: '-1' }] }))).toThrow('positive');
    expect(() => ledger.importOpening(command({ cash: '1.123456789' }))).toThrow('Decimal');
  });

  it('keeps ledger versions independent per portfolio', () => {
    const ledger = new PortfolioLedger();
    expect(ledger.importOpening(command()).ledgerVersion).toBe(1);
    expect(ledger.importOpening(command({ portfolioId: 'portfolio-2', idempotencyKey: 'opening-portfolio-2' })).ledgerVersion).toBe(1);
  });
});
