import { createHash } from 'node:crypto';
import { describe, expect, it } from 'vitest';
import { ExecutionAggregate } from '../../src/domain/execution.js';

const make = () => { const base = { rebalanceBatchId: 'batch-1', decisionId: 'decision-1', proposalVersion: 1, approvalId: 'approval-1', riskEvaluationId: 'risk-1', budgetReservationId: 'budget-1', targetPortfolioVersion: 1, validUntil: '2099-01-01T00:00:00Z', legs: [{ legId: 'leg-1', securityId: 'SSE:600000', side: 'BUY' as const, quantity: '10' }] }; return { ...base, contentHash: createHash('sha256').update(JSON.stringify(base)).digest('hex'), idempotencyKey: 'key-1' }; };
describe('ExecutionAggregate', () => {
  it('原子创建 READY intents 并幂等', () => { const aggregate = new ExecutionAggregate(); const first = aggregate.createApprovedBatch(make()); expect(aggregate.createApprovedBatch(make())).toEqual(first); expect(first.intents[0]?.status).toBe('READY'); });
  it('拒绝过期批准和非法状态跃迁', () => { const aggregate = new ExecutionAggregate(); expect(() => aggregate.createApprovedBatch({ ...make(), validUntil: '2020-01-01T00:00:00Z' })).toThrow('expired'); const batch = aggregate.createApprovedBatch(make()); expect(() => aggregate.transitionIntent(batch.rebalanceBatchId, batch.intents[0]!.intentId, 'FILLED')).toThrow('state transition'); expect(aggregate.transitionIntent(batch.rebalanceBatchId, batch.intents[0]!.intentId, 'SUBMITTED_MANUALLY').status).toBe('SUBMITTED_MANUALLY'); });
});
