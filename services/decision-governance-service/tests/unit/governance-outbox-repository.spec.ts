import { describe, expect, it, vi } from 'vitest';
import { GovernanceOutboxRepository } from '../../src/infrastructure/governance-outbox-repository.js';

describe('GovernanceOutboxRepository', () => {
  it('按 eventId 幂等写入事件并支持发布确认', async () => {
    const query = vi.fn().mockResolvedValue({ rows: [] }); const repository = new GovernanceOutboxRepository({ query });
    const event = { eventId: 'event-1', subject: 'stock.decision-governance.trade-proposal.created.v1', schemaVersion: 1, occurredAt: '2026-09-04T00:00:00Z', availableAt: '2026-09-04T00:00:00Z', producer: 'decision-governance-service', correlationId: 'corr-1', payload: {} };
    await repository.append(event, 'p-1'); await repository.markPublished('event-1');
    expect(query.mock.calls[0]?.[0]).toContain('ON CONFLICT (event_id) DO NOTHING'); expect(query.mock.calls[1]).toEqual(['UPDATE governance_outbox_events SET published_at = now() WHERE event_id = $1 AND published_at IS NULL', ['event-1']]);
  });
  it('批量领取待发布事件并更新租约', async () => { const query = vi.fn().mockResolvedValue({ rows: [{ event_id: 'event-2', subject: 'stock.decision-governance.approval.decided.v1', aggregate_id: 'p-1', payload: {}, available_at: '2026-09-04T00:00:30Z' }] }); const repository = new GovernanceOutboxRepository({ query }); await expect(repository.claim(10)).resolves.toMatchObject([{ eventId: 'event-2', aggregateId: 'p-1' }]); expect(query).toHaveBeenCalledWith(expect.stringContaining("interval '30 seconds'"), [10]); });
});
