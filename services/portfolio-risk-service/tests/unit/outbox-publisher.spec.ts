import { describe, expect, it, vi } from 'vitest';
import { OutboxPublisher } from '../../src/application/outbox-publisher.js';

const event = { eventId: 'event-1', subject: 'stock.portfolio-risk.risk-evaluation.created.v1', aggregateId: 'p-1', payload: {}, availableAt: '2026-09-04T00:00:00Z' };

describe('OutboxPublisher', () => {
  it('发布成功后确认事件', async () => {
    const store = { claimOutboxEvents: vi.fn().mockResolvedValue([event]), markOutboxPublished: vi.fn() };
    const publisher = new OutboxPublisher(store, { publish: vi.fn() });
    await expect(publisher.publishBatch()).resolves.toEqual({ claimed: 1, published: 1, failed: 0 });
    expect(store.markOutboxPublished).toHaveBeenCalledWith('event-1');
  });

  it('发布失败时不确认并返回失败数量', async () => {
    const store = { claimOutboxEvents: vi.fn().mockResolvedValue([event]), markOutboxPublished: vi.fn() };
    const publisher = new OutboxPublisher(store, { publish: vi.fn().mockRejectedValue(new Error('broker down')) });
    await expect(publisher.publishBatch()).resolves.toEqual({ claimed: 1, published: 0, failed: 1 });
    expect(store.markOutboxPublished).not.toHaveBeenCalled();
  });

  it('空队列不调用发布器', async () => {
    const store = { claimOutboxEvents: vi.fn().mockResolvedValue([]), markOutboxPublished: vi.fn() };
    const publish = vi.fn();
    await expect(new OutboxPublisher(store, { publish }).publishBatch()).resolves.toEqual({ claimed: 0, published: 0, failed: 0 });
    expect(publish).not.toHaveBeenCalled();
  });
});
