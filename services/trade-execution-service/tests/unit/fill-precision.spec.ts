import { createHash } from 'node:crypto';
import { describe, expect, it } from 'vitest';
import { ExecutionAggregate } from '../../src/domain/execution.js';
function fixture() {
  const aggregate = new ExecutionAggregate();
  const base = { rebalanceBatchId: 'decimal', decisionId: 'd', proposalVersion: 1, approvalId: 'a', riskEvaluationId: 'r', budgetReservationId: 'b', targetPortfolioVersion: 1, validUntil: '2099-01-01T00:00:00Z', legs: [{ legId: 'l', securityId: 's', side: 'BUY' as const, quantity: '0.3' }] };
  const batch = aggregate.createApprovedBatch({ ...base, contentHash: createHash('sha256').update(JSON.stringify(base)).digest('hex'), idempotencyKey: 'k' });
  const intentId = batch.intents[0]!.intentId;
  aggregate.transitionIntent('decimal', intentId, 'SUBMITTED_MANUALLY');
  const fill = (fillId: string, quantity: string) => ({ fillId, intentId, filledQuantity: quantity, fillPrice: '1.1', occurredAt: '2026-09-05T00:00:00Z', idempotencyKey: fillId });
  return { aggregate, fill };
}
describe('增量成交Decimal与超量边界', () => {
  it('0.1与0.2精确累计为0.3，重复成交无副作用', () => {
    const { aggregate, fill } = fixture();
    expect(aggregate.recordFill('decimal', fill('one', '0.1')).status).toBe('PARTIALLY_FILLED');
    const second = fill('two', '0.2');
    expect(aggregate.recordFill('decimal', second).status).toBe('FILLED');
    expect(aggregate.recordFill('decimal', second).status).toBe('FILLED');
  });
  it('超量与非有限价格不能改变订单，之后可接受正确成交', () => {
    const { aggregate, fill } = fixture();
    expect(() => aggregate.recordFill('decimal', fill('over', '0.4'))).toThrow('exceeds');
    expect(() => aggregate.recordFill('decimal', { ...fill('invalid', '0.1'), fillPrice: 'Infinity' })).toThrow('decimal');
    expect(aggregate.recordFill('decimal', fill('valid', '0.3')).status).toBe('FILLED');
  });
});
