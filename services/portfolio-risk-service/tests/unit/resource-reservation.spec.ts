import { describe, expect, it } from 'vitest';
import { reserveResources, transitionReservation } from '../../src/domain/resource-reservation.js';
import type { ExecutionLeg } from '@stock/contracts';
const snapshot = { snapshotId: 's', portfolioId: 'p', accountId: 'a', asOf: '2026-09-05T00:00:00Z', cash: '100', positions: [{ securityId: 'SSE:600000', quantity: '10', availableQuantity: '8' }], ledgerVersion: 3, sourceRef: 'test', contentHash: 'x' };
const request = (id: string, legs: readonly ExecutionLeg[] = [{ legId: 'b', securityId: 'SSE:600001', side: 'BUY', quantity: '8', limitPrice: '10' }]) => ({ reservationId: id, portfolioId: 'p', ledgerVersion: 3, decisionId: 'd', proposalVersion: 1, riskEvaluationId: 'r', riskPolicyVersion: 'policy-1', executionContentHash: 'a'.repeat(64), feeBuffer: '2', legs, idempotencyKey: id });
describe('ResourceReservation', () => {
  it('预留买入现金和卖出可用量，不计未确认卖出所得', () => {
    const reservation = reserveResources(snapshot, [], request('r', [{ legId: 'sell', securityId: 'SSE:600000', side: 'SELL', quantity: '8', limitPrice: '10' }, { legId: 'buy', securityId: 'SSE:600001', side: 'BUY', quantity: '8', limitPrice: '10' }]));
    expect(reservation.reservedCash).toBe('82');
    expect(reservation.reservedSells).toEqual({ 'SSE:600000': '8' });
  });
  it('拒绝现金不足、超卖、旧版本和第二个活动批次', () => {
    expect(() => reserveResources(snapshot, [], request('cash', [{ legId: 'b', securityId: 'SSE:600001', side: 'BUY', quantity: '11', limitPrice: '10' }]))).toThrow('cash');
    expect(() => reserveResources(snapshot, [], request('sell', [{ legId: 's', securityId: 'SSE:600000', side: 'SELL', quantity: '9', limitPrice: '1' }]))).toThrow('sell');
    expect(() => reserveResources(snapshot, [], { ...request('old'), ledgerVersion: 2 })).toThrow('version');
    const active = reserveResources(snapshot, [], request('active', [{ legId: 'b', securityId: 'SSE:600001', side: 'BUY', quantity: '1', limitPrice: '1' }]));
    expect(() => reserveResources(snapshot, [active], request('second', [{ legId: 'b', securityId: 'SSE:600001', side: 'BUY', quantity: '1', limitPrice: '1' }]))).toThrow('active');
  });
  it('UNKNOWN持续占用，只有明确状态机路径可以释放', () => {
    const reservation = reserveResources(snapshot, [], request('life', [{ legId: 'b', securityId: 'SSE:600001', side: 'BUY', quantity: '1', limitPrice: '1' }]));
    const unknown = transitionReservation(transitionReservation(reservation, 'DISPATCHING'), 'UNKNOWN');
    expect(unknown.status).toBe('UNKNOWN');
    expect(() => transitionReservation(unknown, 'RELEASED')).toThrow('transition');
    expect(transitionReservation(unknown, 'SETTLED').status).toBe('SETTLED');
  });
});
