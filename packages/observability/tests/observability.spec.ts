import { describe, expect, it } from 'vitest';
import { currentTraceContext, readiness, redact, withTraceContext } from '../src/index.js';

describe('observability baseline', () => {
  it('propagates correlation context through asynchronous work', async () => {
    await withTraceContext({ correlationId: 'request-1', causationId: 'event-1' }, async () => {
      await Promise.resolve(); expect(currentTraceContext()?.correlationId).toBe('request-1');
    });
  });
  it('redacts sensitive values', () => expect(redact({ token: 'hidden', nested: { databaseUrl: 'hidden' } })).toEqual({ token: '[REDACTED]', nested: { databaseUrl: '[REDACTED]' } }));
  it('keeps liveness separate from dependency readiness', () => expect(readiness({ postgres: false }).status).toBe('DOWN'));
});
