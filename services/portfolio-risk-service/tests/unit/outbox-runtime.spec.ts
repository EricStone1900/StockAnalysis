import { describe, expect, it, vi } from 'vitest';
import { createOutboxRuntime } from '../../src/application/outbox-runtime.js';

describe('createOutboxRuntime', () => {
  it('组装 Store、JetStream Publisher 和 Worker', async () => {
    const store = { claimOutboxEvents: vi.fn().mockResolvedValue([]), markOutboxPublished: vi.fn() };
    const runtime = createOutboxRuntime(store, { jetstream: () => ({ publish: vi.fn() }) }, 100);
    expect(runtime.worker.isRunning()).toBe(false);
    await expect(runtime.publisher.publishBatch()).resolves.toEqual({ claimed: 0, published: 0, failed: 0 });
    expect(store.claimOutboxEvents).toHaveBeenCalledWith(50);
  });
});
