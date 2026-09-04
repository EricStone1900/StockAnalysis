import { describe, expect, it, vi } from 'vitest';
import { ExecutionBatchEventHandler } from '../../src/application/execution-event-handler.js';

const event = { eventId: 'event-1', subject: 'stock.trade-execution.rebalance-batch.created.v1', payload: { budgetReservationId: 'reservation-1' } } as const;

describe('ExecutionBatchEventHandler', () => {
  it('按 eventId 幂等消费并完成预算消费', async () => {
    const consumeBudget = vi.fn().mockResolvedValue({ status: 'CONSUMED' });
    const handler = new ExecutionBatchEventHandler({ consumeBudget });
    await expect(handler.handle(event)).resolves.toBe(true);
    await expect(handler.handle(event)).resolves.toBe(false);
    expect(consumeBudget).toHaveBeenCalledOnce();
    expect(consumeBudget).toHaveBeenCalledWith('reservation-1');
  });

  it('缺少预算引用或处理失败时不确认事件', async () => {
    const consumeBudget = vi.fn().mockRejectedValue(new Error('reservation is not consumable'));
    const handler = new ExecutionBatchEventHandler({ consumeBudget });
    await expect(handler.handle(event)).rejects.toThrow('not consumable');
    await expect(handler.handle(event)).rejects.toThrow('not consumable');
    await expect(handler.handle({ ...event, eventId: 'event-2', payload: {} })).rejects.toThrow('budget reference');
    await expect(handler.handle({ ...event, subject: 'stock.other.event.v1' })).rejects.toThrow('unsupported');
    expect(consumeBudget).toHaveBeenCalledTimes(2);
  });
});
