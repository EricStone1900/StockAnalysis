import { describe, expect, it } from 'vitest';
import { valuePortfolio } from '../../src/domain/valuation.js';

const snapshot = { snapshotId: 'snapshot-1', portfolioId: 'p-1', accountId: 'a-1', asOf: '2026-09-04T01:00:00Z', cash: '100', positions: [{ securityId: 'SSE:600000', quantity: '10', availableQuantity: '10' }], ledgerVersion: 1, sourceRef: 'test', contentHash: 'hash' } as const;

describe('portfolio valuation', () => {
  it('binds equity to a price version and deterministic market value', () => {
    const value = valuePortfolio(snapshot, [{ securityId: 'SSE:600000', close: '12.34', asOf: '2026-09-04T01:00:00Z' }], 'market-v1', '2026-09-04T01:00:00Z', 5);
    expect(value).toMatchObject({ marketValue: '123.4', totalEquity: '223.4', marketDataVersion: 'market-v1' });
    expect(value.contentHash).toHaveLength(64);
  });

  it('fails closed for missing or stale prices', () => {
    expect(() => valuePortfolio(snapshot, [], 'market-v1', '2026-09-04T01:00:00Z', 5)).toThrow('missing price');
    expect(() => valuePortfolio(snapshot, [{ securityId: 'SSE:600000', close: '12.34', asOf: '2026-09-04T00:00:00Z' }], 'market-v1', '2026-09-04T01:00:00Z', 5)).toThrow('stale price');
  });
});
