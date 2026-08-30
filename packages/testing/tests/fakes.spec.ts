import { describe, expect, it } from 'vitest';
import { FakeEventPublisher } from '../src/index.js';
describe('FakeEventPublisher', () => { it('records published fixtures', async () => { const fake = new FakeEventPublisher<string>(); await fake.publish('event'); expect(fake.events).toEqual(['event']); }); });
