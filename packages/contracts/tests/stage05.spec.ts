import { describe, expect, it } from 'vitest';
import { FakeStage05Publisher } from '../src/stage05.js';

describe('阶段05契约 Fake Publisher', () => { it('按 eventId 幂等并保留 correlationId', async () => { const publisher = new FakeStage05Publisher(); const event = { eventId: 'event-1', subject: 'stock.trade-execution.fill.recorded.v1', correlationId: 'corr-1', payload: { fillId: 'fill-1', intentId: 'intent-1', filledQuantity: '1', fillPrice: '10' } }; await publisher.publish(event); await publisher.publish(event); expect(publisher.events).toHaveLength(1); expect(publisher.events[0]).toMatchObject({ eventId: 'event-1', correlationId: 'corr-1' }); }); });
