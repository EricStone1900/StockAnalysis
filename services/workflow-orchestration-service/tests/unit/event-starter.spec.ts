import { describe, expect, it, vi } from 'vitest';
import { RebalanceExecutionEventStarter } from '../../src/event-starter.js';

const request = { workflowId: 'wf-1', runId: 'run-1', correlationId: 'corr-1', idempotencyKey: 'idem-1', payload: { portfolioId: 'p-1', decisionId: 'd-1', proposalVersion: 1, tradingDate: '2026-09-05', batchSequence: 1 as const, reason: 'DAILY_TARGET' as const, scenario: 'PASS' as const, legCount: 1 } };
function message(event: unknown) { return { data: new TextEncoder().encode(JSON.stringify(event)), ack: vi.fn() }; }

describe('RebalanceExecutionEventStarter', () => {
  it('仅在完整 workflowRequest 存在时启动 Temporal Workflow', async () => {
    const consumer = { [Symbol.asyncIterator]: () => ({ next: async () => ({ done: true, value: undefined }) }), destroy: vi.fn() };
    const subscribe = vi.fn().mockResolvedValue(consumer);
    const client = { workflow: { start: vi.fn().mockResolvedValue(undefined) } };
    const starter = new RebalanceExecutionEventStarter({ jetstream: () => ({ subscribe }) } as never, { streams: { add: vi.fn().mockResolvedValue(undefined) } } as never, client, 'stock-workflows-v1');
    await starter.start();
    expect(subscribe).toHaveBeenCalledWith('stock.trade-execution.rebalance-batch.created.v1', expect.anything());
    expect(client.workflow.start).not.toHaveBeenCalled();
  });

  it('启动配置完整时传递原始请求和幂等 Workflow ID', async () => {
    let resolve!: (value: unknown) => void;
    const waiting = new Promise((r) => { resolve = r; });
    let delivered = false;
    const consumer = { [Symbol.asyncIterator]: () => ({ next: async () => { if (delivered) return { done: true, value: undefined }; delivered = true; const value = await waiting; return { done: false, value }; } }), destroy: vi.fn() };
    const client = { workflow: { start: vi.fn().mockResolvedValue(undefined) } };
    const starter = new RebalanceExecutionEventStarter({ jetstream: () => ({ subscribe: vi.fn().mockResolvedValue(consumer) }) } as never, { streams: { add: vi.fn().mockResolvedValue(undefined) } } as never, client, 'stock-workflows-v1');
    await starter.start(); resolve(message({ eventId: 'event-1', subject: 'stock.trade-execution.rebalance-batch.created.v1', payload: { workflowRequest: request } }));
    await new Promise((r) => setTimeout(r, 0));
    expect(client.workflow.start).toHaveBeenCalledWith('rebalanceExecutionWorkflow', { workflowId: 'rebalance-event-1', taskQueue: 'stock-workflows-v1', args: [request] });
  });
});
