import { describe, expect, it, vi } from 'vitest';
import { ExecutionEventHandler } from '../../src/application/execution-event-handler.js';

const snapshot = { portfolioId: 'portfolio-1', ledgerVersion: 3 } as never;
const fill = { eventId: 'event-1', subject: 'stock.trade-execution.fill.recorded.v1', occurredAt: '2026-09-05T01:00:00Z', correlationId: 'corr-1', payload: { portfolioId: 'portfolio-1', rebalanceBatchId: 'batch-1', resourceReservationId: 'resource-1', securityId: 'SSE:600000', side: 'BUY', filledQuantity: '2', fillPrice: '10', fillId: 'fill-1', intentId: 'intent-1' } } as const;

describe('ExecutionEventHandler', () => {
  it('成交事件只写一次账本并推进资源到 IN_FLIGHT', async () => {
    const recordConfirmedFill = vi.fn(); const transition = vi.fn(); const handler = new ExecutionEventHandler({ latest: vi.fn().mockResolvedValue(snapshot), recordConfirmedFill }, { transition });
    await handler.handle(fill); await handler.handle(fill);
    expect(recordConfirmedFill).toHaveBeenCalledTimes(1); expect(transition).toHaveBeenCalledWith('resource-1', 'IN_FLIGHT');
  });
  it('只有批次完成事件才能结算资源', async () => {
    const transition = vi.fn(); const handler = new ExecutionEventHandler({ latest: vi.fn(), recordConfirmedFill: vi.fn() }, { transition });
    await handler.handle({ eventId: 'event-2', subject: 'stock.trade-execution.rebalance-batch.completed.v1', occurredAt: '2026-09-05T01:00:00Z', payload: { resourceReservationId: 'resource-1' } });
    expect(transition).toHaveBeenCalledWith('resource-1', 'SETTLED');
  });
});
