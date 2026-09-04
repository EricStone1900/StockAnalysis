import { describe, expect, it } from 'vitest';
import { DecisionBudgetReservation } from '../../src/domain/decision-budget.js';

const policy = { maxDailyRebalanceBatches: 2, allowedSecondBatchReasons: ['RISK_REDUCTION'] };
describe('DecisionBudgetReservation', () => {
  it('限制每日两批且第二批校验原因', () => {
    const budget = new DecisionBudgetReservation(); const base = { portfolioId: 'p-1', tradingDate: '2026-09-04', proposalId: 'proposal', kind: 'REBALANCE' as const };
    expect(budget.reserve({ ...base, reservationId: 'r1', reason: 'NORMAL', idempotencyKey: 'k1' }, policy).batchNumber).toBe(1);
    expect(() => budget.reserve({ ...base, reservationId: 'r2', reason: 'NORMAL', idempotencyKey: 'k2' }, policy)).toThrow('second rebalance batch reason');
    expect(budget.reserve({ ...base, reservationId: 'r2', reason: 'RISK_REDUCTION', idempotencyKey: 'k2' }, policy).batchNumber).toBe(2);
    expect(() => budget.reserve({ ...base, reservationId: 'r3', reason: 'RISK_REDUCTION', idempotencyKey: 'k3' }, policy)).toThrow('daily rebalance batch limit');
  });
  it('HOLD 不占用批次且重复键幂等', () => { const budget = new DecisionBudgetReservation(); const input = { reservationId: 'hold', portfolioId: 'p', tradingDate: '2026-09-04', proposalId: 'hold-p', kind: 'HOLD' as const, reason: 'hold', idempotencyKey: 'hold-key' }; expect(budget.reserve(input, policy).batchNumber).toBe(0); expect(budget.reserve(input, policy).status).toBe('RELEASED'); });
  it('执行闭环为 RESERVED→DISPATCHING→CONSUMED，消费后不可释放或再次占用', () => { const budget = new DecisionBudgetReservation(); const base = { reservationId: 'r1', portfolioId: 'p-1', tradingDate: '2026-09-04', proposalId: 'proposal', kind: 'REBALANCE' as const, reason: 'NORMAL', idempotencyKey: 'k1' }; expect(budget.reserve(base, policy).status).toBe('RESERVED'); expect(budget.markDispatching('r1').status).toBe('DISPATCHING'); expect(budget.consume('r1').status).toBe('CONSUMED'); expect(budget.consume('r1').status).toBe('CONSUMED'); expect(() => budget.release('r1')).toThrow('cannot be released'); expect(budget.reserve({ ...base, reservationId: 'r2', reason: 'RISK_REDUCTION', idempotencyKey: 'k2' }, policy).batchNumber).toBe(2); expect(() => budget.reserve({ ...base, reservationId: 'r3', reason: 'RISK_REDUCTION', idempotencyKey: 'k3' }, policy)).toThrow('daily rebalance batch limit'); });
  it('未发送的预留可释放并重新占用批次', () => { const budget = new DecisionBudgetReservation(); const base = { portfolioId: 'p-1', tradingDate: '2026-09-04', proposalId: 'proposal', kind: 'REBALANCE' as const, reason: 'NORMAL' }; expect(budget.reserve({ ...base, reservationId: 'r1', idempotencyKey: 'k1' }, policy).batchNumber).toBe(1); expect(budget.release('r1').status).toBe('RELEASED'); expect(budget.reserve({ ...base, reservationId: 'r2', idempotencyKey: 'k2' }, policy).batchNumber).toBe(1); });
});
