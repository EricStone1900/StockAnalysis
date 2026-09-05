import { describe, expect, it } from 'vitest';
import { FakeAnalysisEntrypoints } from '../../src/application/agent-entrypoints.js';

describe('agent entrypoints', () => {
  it('is idempotent across HTTP, NATS and Temporal entry adapters', async () => {
    const entrypoints = new FakeAnalysisEntrypoints();
    const command = { correlationId: 'corr-1', text: 'hello' };
    const http = await entrypoints.execute(command);
    const nats = await entrypoints.consumeNats(command);
    const temporal = await entrypoints.temporalActivity(command);
    expect(nats.runId).toBe(http.runId);
    expect(temporal.runId).toBe(http.runId);
  });
});
