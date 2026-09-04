import { describe, expect, it, vi } from 'vitest';
import { GovernanceOutboxWorker } from '../../src/application/outbox-worker.js';

const event = { eventId: 'event-1', subject: 'stock.decision-governance.trade-proposal.created.v1', aggregateId: 'p-1', payload: {}, availableAt: '2026-09-04T00:00:00Z' };
describe('GovernanceOutboxWorker', () => {
  it('发布成功后确认', async () => { const store = { claim: vi.fn().mockResolvedValue([event]), markPublished: vi.fn() }; const worker = new GovernanceOutboxWorker(store, { publish: vi.fn() }); await expect(worker.publishBatch()).resolves.toEqual({ claimed: 1, published: 1, failed: 0 }); expect(store.markPublished).toHaveBeenCalledWith('event-1'); });
  it('发布失败保留未确认状态', async () => { const store = { claim: vi.fn().mockResolvedValue([event]), markPublished: vi.fn() }; const worker = new GovernanceOutboxWorker(store, { publish: vi.fn().mockRejectedValue(new Error('NATS unavailable')) }); await expect(worker.publishBatch()).resolves.toEqual({ claimed: 1, published: 0, failed: 1 }); expect(store.markPublished).not.toHaveBeenCalled(); });
});
