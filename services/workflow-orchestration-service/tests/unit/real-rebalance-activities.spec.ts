import { describe, expect, it, vi } from 'vitest';
import { HttpRebalanceExecutionActivities } from '../../src/activities/real-rebalance-activities.js';

const request = { workflowId: 'wf-1', runId: 'run-1', correlationId: 'corr-1', idempotencyKey: 'idem-1', payload: { portfolioId: 'p-1', decisionId: 'd-1', proposalId: 'proposal-1', proposalVersion: 1, tradingDate: '2026-09-05', batchSequence: 1 as const, reason: 'DAILY_TARGET' as const, scenario: 'PASS' as const, legCount: 1, budgetReservationId: 'budget-1' } };

describe('HttpRebalanceExecutionActivities', () => {
  it('预算预留使用治理服务身份和幂等键', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ reservationId: 'budget-1', status: 'RESERVED' }), { status: 201 }));
    const activities = new HttpRebalanceExecutionActivities({ governanceBaseUrl: 'http://governance', portfolioBaseUrl: 'http://portfolio', executionBaseUrl: 'http://execution', governanceToken: 'g', portfolioToken: 'p', executionToken: 'e' }, { fetch: fetchMock });
    const result = await activities.reserveBudget(request);
    expect(result.result.reservationStatus).toBe('RESERVED');
    expect(fetchMock).toHaveBeenCalledWith('http://governance/api/v1/proposals/proposal-1/budget-reservations', expect.objectContaining({ method: 'POST', headers: expect.objectContaining({ 'x-service-token': 'g', 'Idempotency-Key': 'idem-1' }) }));
  });

  it('缺少真实授权引用时拒绝构造执行批次', async () => {
    const activities = new HttpRebalanceExecutionActivities({ governanceBaseUrl: 'g', portfolioBaseUrl: 'p', executionBaseUrl: 'e', governanceToken: 'g', portfolioToken: 'p', executionToken: 'e' });
    await expect(activities.createRebalanceBatch(request)).rejects.toThrow('execution command is incomplete');
  });
});
