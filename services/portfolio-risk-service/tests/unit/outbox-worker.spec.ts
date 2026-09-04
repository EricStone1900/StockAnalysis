import { afterEach, describe, expect, it, vi } from 'vitest';
import { OutboxWorker } from '../../src/application/outbox-publisher.js';

afterEach(() => vi.useRealTimers());

describe('OutboxWorker', () => {
  it('可幂等启动并按间隔执行发布批次', async () => {
    vi.useFakeTimers();
    const publisher = { publishBatch: vi.fn().mockResolvedValue({ claimed: 0, published: 0, failed: 0 }) };
    const worker = new OutboxWorker(publisher, 100);
    worker.start(); worker.start();
    await vi.advanceTimersByTimeAsync(250);
    expect(publisher.publishBatch).toHaveBeenCalledTimes(2);
    expect(worker.isRunning()).toBe(true);
    worker.stop();
    expect(worker.isRunning()).toBe(false);
  });

  it('发布器异常不会终止后续轮询', async () => {
    vi.useFakeTimers();
    const publisher = { publishBatch: vi.fn().mockRejectedValue(new Error('temporary failure')) };
    const worker = new OutboxWorker(publisher, 100);
    worker.start();
    await vi.advanceTimersByTimeAsync(210);
    expect(publisher.publishBatch).toHaveBeenCalledTimes(2);
    worker.stop();
  });
});
