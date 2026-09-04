import { describe, expect, it } from 'vitest';
import { ProposalController } from '../../src/bootstrap/main.js';

describe('ProposalController budget API', () => {
  it('创建并释放调仓批次预留', async () => {
    const controller = new ProposalController();
    const input = { reservationId: 'r-api', portfolioId: 'p-api', tradingDate: '2026-09-04', reason: 'NORMAL', kind: 'REBALANCE' as const, idempotencyKey: 'r-api-key', policy: { maxDailyRebalanceBatches: 2, allowedSecondBatchReasons: [] } };
    await expect(controller.reserveBudget('proposal-api', input)).resolves.toMatchObject({ batchNumber: 1, status: 'RESERVED' });
    await expect(controller.releaseBudget('r-api')).resolves.toMatchObject({ status: 'RELEASED' });
  });
});
