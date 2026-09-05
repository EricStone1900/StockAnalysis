import { describe, expect, it } from 'vitest';
import { FakeAnalysisEntrypoints } from '../../src/application/agent-entrypoints.js';
import { InMemoryAgentRunRepository } from '../../src/application/agent-run-repository.js';

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

  it('recovers a completed run after an entrypoint process restart', async () => {
    const repository = new InMemoryAgentRunRepository();
    const firstProcess = new FakeAnalysisEntrypoints(repository);
    const original = await firstProcess.execute({ correlationId: 'corr-restart', text: 'artifact-ref' });
    const restartedProcess = new FakeAnalysisEntrypoints(repository);
    const recovered = await restartedProcess.execute({ correlationId: 'corr-restart', text: 'ignored-on-retry' });
    expect(recovered).toEqual(original);
  });
});
