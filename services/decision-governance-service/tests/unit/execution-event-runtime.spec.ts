import { describe, expect, it, vi } from 'vitest';
import { ExecutionBatchEventHandler } from '../../src/application/execution-event-handler.js';
import { GovernanceExecutionEventRuntime } from '../../src/application/execution-event-runtime.js';

describe('GovernanceExecutionEventRuntime', () => {
  it('订阅执行批次事件、解码并在停止时取消订阅', async () => {
    let callback: ((payload: Uint8Array) => Promise<void>) | undefined;
    const unsubscribe = vi.fn();
    const subscribe = vi.fn().mockImplementation(async (_subject: string, handler: (payload: Uint8Array) => Promise<void>) => { callback = handler; return { unsubscribe }; });
    const consumeBudget = vi.fn().mockResolvedValue({ status: 'CONSUMED' });
    const runtime = new GovernanceExecutionEventRuntime({ subscribe }, new ExecutionBatchEventHandler({ consumeBudget }));
    await runtime.start(); await runtime.start();
    expect(subscribe).toHaveBeenCalledOnce(); expect(runtime.isRunning()).toBe(true);
    await callback!(new TextEncoder().encode(JSON.stringify({ eventId: 'e1', subject: 'stock.trade-execution.rebalance-batch.created.v1', payload: { budgetReservationId: 'r1' } })));
    expect(consumeBudget).toHaveBeenCalledWith('r1');
    await runtime.stop(); await runtime.stop();
    expect(unsubscribe).toHaveBeenCalledOnce(); expect(runtime.isRunning()).toBe(false);
  });
});
