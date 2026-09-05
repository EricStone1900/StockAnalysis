import { beforeEach, describe, expect, it, vi } from 'vitest';
const activities = vi.hoisted(() => ({ reserveBudget: vi.fn(), createRebalanceBatch: vi.fn(), createManualOrderIntents: vi.fn(), recordFills: vi.fn(), releaseBudget: vi.fn() }));
vi.mock('@temporalio/workflow', () => ({ proxyActivities: () => activities }));
import { rebalanceExecutionWorkflow } from '../../src/workflows/rebalance-execution.workflow.js';
import type { RebalanceExecutionRequest } from '../../src/workflows/rebalance-execution.contract.js';
const request: RebalanceExecutionRequest = { workflowId: 'w', runId: 'r', correlationId: 'c', idempotencyKey: 'k', payload: { portfolioId: 'p', decisionId: 'd', proposalVersion: 1, tradingDate: '2026-09-05', batchSequence: 1, reason: 'DAILY_TARGET', scenario: 'PASS', legCount: 1 } };
const response = (extra = {}) => ({ result: { artifactRef: { uri: 'artifact://test', contentHash: 'a'.repeat(64) }, ...extra } });
describe('实际Workflow函数的异常恢复', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    activities.reserveBudget.mockResolvedValue(response({ reservationStatus: 'RESERVED' }));
    activities.createRebalanceBatch.mockResolvedValue(response({ accepted: true }));
    activities.createManualOrderIntents.mockResolvedValue(response());
    activities.recordFills.mockResolvedValue(response({ fillStatus: 'COMPLETE' }));
    activities.releaseBudget.mockResolvedValue(response({ reservationStatus: 'RELEASED' }));
  });
  it('接受请求超时不能推断未接受或释放预算', async () => {
    activities.createRebalanceBatch.mockRejectedValue(new Error('response lost'));
    expect((await rebalanceExecutionWorkflow(request)).status).toBe('UNKNOWN');
    expect(activities.releaseBudget).not.toHaveBeenCalled();
  });
  it('接受后成交步骤失败保留预算', async () => {
    activities.recordFills.mockRejectedValue(new Error('worker disconnected'));
    expect((await rebalanceExecutionWorkflow(request)).status).toBe('UNKNOWN');
    expect(activities.releaseBudget).not.toHaveBeenCalled();
  });
  it('只有明确未接受才释放', async () => {
    activities.createRebalanceBatch.mockResolvedValue(response({ accepted: false }));
    expect((await rebalanceExecutionWorkflow(request)).status).toBe('RELEASED');
    expect(activities.releaseBudget).toHaveBeenCalledOnce();
  });
});
