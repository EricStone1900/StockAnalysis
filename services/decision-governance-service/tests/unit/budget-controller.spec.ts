import { describe, expect, it } from 'vitest';
import { ProposalController } from '../../src/bootstrap/main.js';

describe('ProposalController budget API', () => {
  it('创建并释放调仓批次预留', async () => {
    const controller = new ProposalController();
    const input = { reservationId: 'r-api', portfolioId: 'p-api', tradingDate: '2026-09-04', reason: 'NORMAL', kind: 'REBALANCE' as const, idempotencyKey: 'r-api-key', policy: { maxDailyRebalanceBatches: 2, allowedSecondBatchReasons: [] } };
    await expect(controller.reserveBudget('proposal-api', input)).resolves.toMatchObject({ batchNumber: 1, status: 'RESERVED' });
    await expect(controller.releaseBudget('r-api')).resolves.toMatchObject({ status: 'RELEASED' });
  });
  it('通过API推进发送中和消费状态，并拒绝消费前释放后的预留', async () => {
    const controller = new ProposalController();
    const input = { reservationId: 'r-lifecycle', portfolioId: 'p-api', tradingDate: '2026-09-04', reason: 'NORMAL', kind: 'REBALANCE' as const, idempotencyKey: 'r-lifecycle-key', policy: { maxDailyRebalanceBatches: 2, allowedSecondBatchReasons: [] } };
    await controller.reserveBudget('proposal-api', input);
    await expect(controller.markBudgetDispatching('r-lifecycle')).resolves.toMatchObject({ status: 'DISPATCHING' });
    await expect(controller.consumeBudget('r-lifecycle')).resolves.toMatchObject({ status: 'CONSUMED' });
    await expect(controller.consumeBudget('r-lifecycle')).resolves.toMatchObject({ status: 'CONSUMED' });
    await expect(controller.releaseBudget('r-lifecycle')).rejects.toThrow('consumed reservation cannot be released');
  });
});
