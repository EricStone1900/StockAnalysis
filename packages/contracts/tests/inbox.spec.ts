import { describe, expect, it } from 'vitest';
import { InMemoryInbox } from '../src/index.js';

it('handles repeated event IDs exactly once', async () => {
  const inbox = new InMemoryInbox(); let calls = 0;
  for (let index = 0; index < 10; index += 1) await inbox.once('event-1', async () => { calls += 1; });
  expect(calls).toBe(1);
});
