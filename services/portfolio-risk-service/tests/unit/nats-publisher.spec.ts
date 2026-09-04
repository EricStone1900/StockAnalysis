import { describe, expect, it, vi } from 'vitest';
import { NatsJetStreamPublisher } from '../../src/application/outbox-publisher.js';

describe('NatsJetStreamPublisher', () => {
  it('以事件主题和 JSON payload 发布到 JetStream', async () => {
    const publish = vi.fn().mockResolvedValue(undefined);
    const publisher = new NatsJetStreamPublisher({ jetstream: () => ({ publish }) });
    await publisher.publish({ eventId: 'event-1', subject: 'stock.portfolio-risk.risk-evaluation.created.v1', aggregateId: 'p-1', payload: { eventId: 'event-1', schemaVersion: 1, occurredAt: '2026-09-04T00:00:00Z', availableAt: '2026-09-04T00:00:00Z', producer: 'portfolio-risk-service', correlationId: 'corr-1', payload: { evaluation: { verdict: 'PASS' } } }, availableAt: '2026-09-04T00:00:00Z' });
    expect(publish).toHaveBeenCalledWith('stock.portfolio-risk.risk-evaluation.created.v1', expect.any(Uint8Array));
    expect(new TextDecoder().decode(publish.mock.calls[0]?.[1])).toContain('event-1');
  });
});
