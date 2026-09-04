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

  it('creates an immutable reversal and rejects a second reversal', () => {
    const ledger = new PortfolioLedger();
    const opening = ledger.importOpening(command());
    const reversal = ledger.reverse({ portfolioId: 'portfolio-1', originalEntryId: `ledger-entry-${opening.snapshotId}`, occurredAt: opening.asOf, availableAt: opening.asOf, sourceRef: 'reversal-1', actorId: 'operator-1', reason: '冲正', expectedVersion: 1, idempotencyKey: 'reversal-key' });
    expect(reversal.type).toBe('REVERSAL');
    expect(reversal.amount).toBe('-100000.00');
    expect(ledger.reverse({ portfolioId: 'portfolio-1', originalEntryId: `ledger-entry-${opening.snapshotId}`, occurredAt: opening.asOf, availableAt: opening.asOf, sourceRef: 'reversal-1', actorId: 'operator-1', reason: '冲正', expectedVersion: 99, idempotencyKey: 'reversal-key' })).toEqual(reversal);
    expect(() => ledger.reverse({ portfolioId: 'portfolio-1', originalEntryId: `ledger-entry-${opening.snapshotId}`, occurredAt: opening.asOf, availableAt: opening.asOf, sourceRef: 'reversal-2', actorId: 'operator-1', reason: '重复冲正', expectedVersion: 2, idempotencyKey: 'reversal-key-2' })).toThrow('already reversed');
  });

  it('restores the latest snapshot into the in-memory view', () => {
    const source = new PortfolioLedger();
    const snapshot = source.importOpening(command());
    const restored = new PortfolioLedger();
    restored.restoreSnapshot(snapshot);
    expect(restored.latest('portfolio-1')).toEqual(snapshot);
    expect(restored.importOpening(command({ idempotencyKey: 'opening-2', expectedVersion: 1 })).ledgerVersion).toBe(2);
  });

  it('records buy and sell fills using Decimal cash and position arithmetic', () => {
    const ledger = new PortfolioLedger();
    ledger.importOpening(command({ cash: '1000', positions: [] }));
    const buy = ledger.recordConfirmedFill({ portfolioId: 'portfolio-1', securityId: 'SSE:600000', side: 'BUY', quantity: '10', price: '12.34', fee: '0.50', occurredAt: '2026-09-03T02:00:00Z', availableAt: '2026-09-03T02:00:00Z', sourceRef: 'fill-1', actorId: 'operator-1', reason: '确认买入', expectedVersion: 1, idempotencyKey: 'fill-1' });
    expect(buy.cash).toBe('876.1'); expect(buy.positions[0]).toMatchObject({ securityId: 'SSE:600000', quantity: '10' });
    const sell = ledger.recordConfirmedFill({ portfolioId: 'portfolio-1', securityId: 'SSE:600000', side: 'SELL', quantity: '4', price: '15', fee: '0.10', occurredAt: '2026-09-03T03:00:00Z', availableAt: '2026-09-03T03:00:00Z', sourceRef: 'fill-2', actorId: 'operator-1', reason: '确认卖出', expectedVersion: 2, idempotencyKey: 'fill-2' });
    expect(sell.cash).toBe('936'); expect(sell.positions[0]?.quantity).toBe('6');
  });

  it('rejects a sell exceeding the available position', () => {
    const ledger = new PortfolioLedger(); ledger.importOpening(command({ positions: [] }));
    expect(() => ledger.recordConfirmedFill({ portfolioId: 'portfolio-1', securityId: 'SSE:600000', side: 'SELL', quantity: '1', price: '1', fee: '0', occurredAt: '2026-09-03T02:00:00Z', availableAt: '2026-09-03T02:00:00Z', sourceRef: 'fill', actorId: 'operator-1', reason: '卖出', expectedVersion: 1, idempotencyKey: 'fill' })).toThrow('exceeds');
  });

  it('records a cash dividend from the current position quantity', () => {
    const ledger = new PortfolioLedger();
    ledger.importOpening(command({ cash: '1000', positions: [{ securityId: 'SSE:600000', quantity: '100' }] }));
    const snapshot = ledger.recordCashDividend({ portfolioId: 'portfolio-1', securityId: 'SSE:600000', cashPerShare: '0.25', occurredAt: '2026-09-03T04:00:00Z', availableAt: '2026-09-03T04:00:00Z', sourceRef: 'dividend-1', actorId: 'operator-1', reason: '现金分红', expectedVersion: 1, idempotencyKey: 'dividend-1' });
    expect(snapshot.cash).toBe('1025'); expect(snapshot.positions[0]?.quantity).toBe('100'); expect(snapshot.ledgerVersion).toBe(2);
  });

  it('adjusts position quantity without changing cash for a stock split', () => {
    const ledger = new PortfolioLedger();
    ledger.importOpening(command({ cash: '1000', positions: [{ securityId: 'SSE:600000', quantity: '100' }] }));
    const snapshot = ledger.recordStockSplit({ portfolioId: 'portfolio-1', securityId: 'SSE:600000', numerator: 2, denominator: 1, occurredAt: '2026-09-03T05:00:00Z', availableAt: '2026-09-03T05:00:00Z', sourceRef: 'split-1', actorId: 'operator-1', reason: '二拆一', expectedVersion: 1, idempotencyKey: 'split-1' });
    expect(snapshot.cash).toBe('1000'); expect(snapshot.positions[0]?.quantity).toBe('200'); expect(snapshot.ledgerVersion).toBe(2);
  });
});
