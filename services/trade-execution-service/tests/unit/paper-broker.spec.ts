import { describe, expect, it } from 'vitest';
import { PaperBrokerAdapter, type PaperOrderCommand } from '../../src/application/paper-broker.js';

const command = (overrides: Partial<PaperOrderCommand> = {}): PaperOrderCommand => ({
  paperAccountId: 'paper-alpha', clientOrderId: 'paper-order-1', rebalanceBatchId: 'paper-batch-1', intentId: 'intent-1', securityId: 'SSE:600000', side: 'BUY', quantity: '100',
  market: { availableAt: '2026-09-05T08:00:00Z', referencePrice: '10', tradable: true, upperLimit: '11', lowerLimit: '9', maxFillQuantity: '40' }, ...overrides,
});

describe('PaperBrokerAdapter', () => {
  it('simulates deterministic partial fills without real-account access', () => {
    const first = new PaperBrokerAdapter('seed-1').place(command());
    const repeat = new PaperBrokerAdapter('seed-1').place(command());
    expect(first).toEqual(repeat);
    expect(first.status).toBe('PARTIALLY_FILLED');
    expect(first.fills[0]?.quantity).toBe('40.00000000');
  });

  it('rejects non-paper accounts, halts, and unmarketable limits', () => {
    const adapter = new PaperBrokerAdapter('seed-1');
    expect(adapter.place(command({ paperAccountId: 'production-alpha' })).rejectionReason).toBe('PAPER_ACCOUNT_REQUIRED');
    expect(adapter.place(command({ clientOrderId: 'halted', market: { ...command().market, tradable: false } })).rejectionReason).toBe('NOT_TRADABLE');
    expect(adapter.place(command({ clientOrderId: 'limit', limitPrice: '9' })).rejectionReason).toBe('LIMIT_PRICE_NOT_MARKETABLE');
  });

  it('is idempotent and supports cancellation only before a complete fill', () => {
    const adapter = new PaperBrokerAdapter('seed-1');
    const placed = adapter.place(command());
    expect(adapter.place(command())).toEqual(placed);
    expect(adapter.cancel('paper-order-1').status).toBe('CANCELLED');
    const filled = adapter.place(command({ clientOrderId: 'filled', quantity: '10', market: { ...command().market, maxFillQuantity: '10' } }));
    expect(adapter.cancel(filled.clientOrderId).status).toBe('FILLED');
  });
});
