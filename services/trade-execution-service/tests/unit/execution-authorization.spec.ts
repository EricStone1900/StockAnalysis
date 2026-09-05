import { createHash } from 'node:crypto';
import { describe, expect, it, vi } from 'vitest';
import { ExecutionService } from '../../src/application/execution-service.js';

describe('执行授权失败关闭', () => {
  const command = () => {
    const base = { rebalanceBatchId: 'auth-batch', decisionId: 'd', proposalVersion: 1, approvalId: 'invented', riskEvaluationId: 'invented', budgetReservationId: 'invented', targetPortfolioVersion: 1, validUntil: '2099-01-01T00:00:00Z', legs: [{ legId: 'l', securityId: 's', side: 'BUY' as const, quantity: '1' }] };
    return { ...base, contentHash: createHash('sha256').update(JSON.stringify(base)).digest('hex'), idempotencyKey: 'auth-key' };
  };
  it('自行填写审批ID及正确Hash也不能在默认配置下创建READY', async () => {
    await expect(new ExecutionService().createBatch(command())).rejects.toThrow('authorization adapter');
  });
  it('权威授权拒绝不被吞掉，也不创建批次', async () => {
    const assertAuthorized = vi.fn().mockRejectedValue(new Error('approval revoked'));
    const service = new ExecutionService(undefined, undefined, undefined, undefined, { assertAuthorized });
    await expect(service.createBatch(command())).rejects.toThrow('approval revoked');
    await expect(service.transitionIntent('auth-batch', 'missing', 'SUBMITTED_MANUALLY')).rejects.toThrow('not found');
  });
});
