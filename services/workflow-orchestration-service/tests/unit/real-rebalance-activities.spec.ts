import { describe, expect, it, vi } from 'vitest';
import { HttpRebalanceExecutionActivities } from '../../src/activities/real-rebalance-activities.js';

const request = { workflowId: 'wf-1', runId: 'run-1', correlationId: 'corr-1', idempotencyKey: 'idem-1', payload: { portfolioId: 'p-1', decisionId: 'd-1', proposalId: 'proposal-1', proposalVersion: 1, tradingDate: '2026-09-05', batchSequence: 1 as const, reason: 'DAILY_TARGET' as const, scenario: 'PASS' as const, legCount: 1, budgetReservationId: 'budget-1', resourceReservationId: 'resource-1' } };

describe('HttpRebalanceExecutionActivities', () => {
  it('预算预留使用治理服务身份和幂等键', async () => {
    const fetchMock = vi.fn().mockImplementation(async () => new Response(JSON.stringify({ reservationId: 'budget-1', status: 'RESERVED' }), { status: 201 }));
    const activities = new HttpRebalanceExecutionActivities({ governanceBaseUrl: 'http://governance', portfolioBaseUrl: 'http://portfolio', executionBaseUrl: 'http://execution', governanceToken: 'g', portfolioToken: 'p', executionToken: 'e' }, { fetch: fetchMock });
    const result = await activities.reserveBudget(request);
    expect(result.result.reservationStatus).toBe('RESERVED');
    expect(fetchMock).toHaveBeenNthCalledWith(1, 'http://governance/api/v1/proposals/proposal-1/budget-reservations', expect.objectContaining({ method: 'POST', headers: expect.objectContaining({ 'x-service-token': 'g', 'Idempotency-Key': 'budget-1' }) }));
    expect(fetchMock).toHaveBeenNthCalledWith(2, 'http://governance/api/v1/proposals/proposal-1/budget-reservations/budget-1/dispatching', expect.objectContaining({ method: 'POST' }));
    expect(fetchMock).toHaveBeenNthCalledWith(3, 'http://portfolio/internal/v1/portfolio-reservations/resource-1/status', expect.objectContaining({ method: 'POST', body: JSON.stringify({ status: 'DISPATCHING' }) }));
  });

  it('将工作流成交价格映射为执行服务要求的 fillPrice', async () => {
    const fetchMock = vi.fn().mockImplementation(async () => new Response(JSON.stringify({}), { status: 201 }));
    const activities = new HttpRebalanceExecutionActivities({ governanceBaseUrl: 'g', portfolioBaseUrl: 'p', executionBaseUrl: 'http://execution', governanceToken: 'g', portfolioToken: 'p', executionToken: 'e' }, { fetch: fetchMock });
    const fillRequest = { ...request, payload: { ...request.payload, legs: [{ legId: 'leg-1', securityId: 'SSE:600000', side: 'BUY' as const, quantity: '10', limitPrice: '100' }], fills: [{ fillId: 'fill-1', intentId: 'order-intent-rebalance-wf-1-leg-1', filledQuantity: '10', fillPrice: '100', occurredAt: '2026-09-05T10:00:00Z', idempotencyKey: 'fill-1' }] } };
    await activities.recordFills(fillRequest);
    expect(fetchMock).toHaveBeenCalledWith('http://execution/api/v1/execution/batches/rebalance-wf-1/fills', expect.objectContaining({ body: expect.stringContaining('"fillPrice":"100"') }));
  });

  it('缺少真实授权引用时拒绝构造执行批次', async () => {
    const activities = new HttpRebalanceExecutionActivities({ governanceBaseUrl: 'g', portfolioBaseUrl: 'p', executionBaseUrl: 'e', governanceToken: 'g', portfolioToken: 'p', executionToken: 'e' });
    await expect(activities.createRebalanceBatch(request)).rejects.toThrow('execution command is incomplete');
  });
});
