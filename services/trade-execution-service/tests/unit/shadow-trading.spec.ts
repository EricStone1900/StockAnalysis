import { describe, expect, it } from 'vitest';
import { ShadowTradingLedger, type ShadowDecision } from '../../src/application/shadow-trading.js';

const decision: ShadowDecision = {
  decisionId: 'decision-shadow-1', proposalVersion: 1, scenario: 'DAILY_WITH_RISK_REDUCTION', decisionAsOf: '2026-09-05T08:00:00Z', policyVersion: 'monitor-v1',
  legs: [{ legId: 'leg-1', securityId: 'SSE:600000', side: 'BUY', quantity: '100' }],
  market: { 'SSE:600000': { availableAt: '2026-09-05T07:59:00Z', referencePrice: '10', tradable: true, maxFillQuantity: '40' } },
};

describe('ShadowTradingLedger', () => {
  it('records a theoretical result in a separate SHADOW episode and never writes to a broker', () => {
    const ledger = new ShadowTradingLedger();
    const report = ledger.record(decision);
    expect(report.episodeType).toBe('SHADOW');
    expect(report.legResults[0]?.theoreticalQuantity).toBe('40.00000000');
    expect(report.contentHash).toHaveLength(64);
  });

  it('is idempotent and rejects future market data from theoretical execution', () => {
    const ledger = new ShadowTradingLedger();
    const first = ledger.record(decision);
    expect(ledger.record(decision)).toEqual(first);
    const future = ledger.record({ ...decision, decisionId: 'decision-shadow-future', market: { 'SSE:600000': { ...decision.market['SSE:600000']!, availableAt: '2026-09-05T09:00:00Z' } } });
    expect(future.legResults[0]?.reason).toBe('FUTURE_MARKET_DATA');
  });

  it('keeps non-tradable legs as explicit differences instead of forcing fills', () => {
    const report = new ShadowTradingLedger().record({ ...decision, decisionId: 'decision-shadow-halt', market: { 'SSE:600000': { ...decision.market['SSE:600000']!, tradable: false } } });
    expect(report.differences).toEqual(['leg-1:NOT_TRADABLE']);
    expect(report.legResults[0]?.executable).toBe(false);
  });
});
