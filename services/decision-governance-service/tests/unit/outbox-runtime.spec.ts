import { describe, expect, it, vi } from 'vitest';
import { GovernanceNatsPublisher, GovernanceWorkerLifecycle } from '../../src/application/outbox-runtime.js';

describe('Governance Outbox runtime', () => {
  it('发布器编码事件并转发生命周期', async () => { const publish = vi.fn().mockResolvedValue(undefined); await new GovernanceNatsPublisher({ jetstream: () => ({ publish }) }).publish({ eventId: 'e1', subject: 'stock.decision-governance.trade-proposal.created.v1', aggregateId: 'p1', payload: {}, availableAt: '2026-09-04T00:00:00Z' }); expect(publish).toHaveBeenCalledWith(expect.stringContaining('trade-proposal'), expect.any(Uint8Array)); const worker = { start: vi.fn(), stop: vi.fn() }; const lifecycle = new GovernanceWorkerLifecycle(worker); lifecycle.onApplicationBootstrap(); lifecycle.onApplicationShutdown(); expect(worker.start).toHaveBeenCalledOnce(); expect(worker.stop).toHaveBeenCalledOnce(); });
});
