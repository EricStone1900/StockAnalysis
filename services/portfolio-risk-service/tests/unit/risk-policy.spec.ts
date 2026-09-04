import { describe, expect, it } from 'vitest';
import { evaluateRisk, type RiskPolicy } from '../../src/domain/risk-policy.js';

const policy: RiskPolicy = { policyVersion: 'policy-v1', maxPositionWeight: '0.6', maxTotalPositionWeight: '0.9', minCash: '100', maxTurnover: '500', maxDailyRebalanceBatches: 2, allowedSecondBatchReasons: ['RISK_REDUCTION'], maxDrawdown: '200', paused: false };
const portfolio = { snapshotId: 's1', portfolioId: 'p1', accountId: 'a1', asOf: '2026-09-01T00:00:00Z', cash: '500', positions: [{ securityId: 'SSE:600000', quantity: '10', availableQuantity: '10' }], ledgerVersion: 1, sourceRef: 'test', contentHash: 'hash' };

describe('RiskPolicy', () => {
  it('评估完整Leg集合并通过合法提案', () => {
    const result = evaluateRisk({ proposalId: 'proposal-1', reason: 'RISK_REDUCTION', legs: [{ securityId: 'SSE:600000', side: 'BUY', quantity: '2', price: '10' }], portfolio, prices: { 'SSE:600000': '10' }, decisionBudget: { rebalanceBatchesToday: 0 }, peakEquity: '600', policy });
    expect(result.verdict).toBe('PASS');
    expect(result.projectedAfter.cash).toBe('480');
  });

  it('对暂停、第三批次和现金不足失败关闭', () => {
    const result = evaluateRisk({ proposalId: 'proposal-2', reason: 'NORMAL', legs: [{ securityId: 'SSE:600000', side: 'BUY', quantity: '50', price: '10' }], portfolio, prices: { 'SSE:600000': '10' }, decisionBudget: { rebalanceBatchesToday: 2 }, peakEquity: '600', policy: { ...policy, paused: true } });
    expect(result.verdict).toBe('REJECT');
    expect(result.rules.filter((rule) => rule.verdict === 'REJECT').map((rule) => rule.reasonCode)).toEqual(expect.arrayContaining(['GLOBAL_PAUSE', 'DAILY_BATCH_LIMIT', 'MIN_CASH']));
  });
});
