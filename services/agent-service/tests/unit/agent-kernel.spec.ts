import { describe, expect, it } from 'vitest';
import { AgentRunner, fakeAnalysisDefinition } from '../../src/application/agent-kernel.js';

describe('agent kernel', () => {
  it('runs fake analysis with validated structured output and correlation audit', async () => {
    const result = await new AgentRunner().run(fakeAnalysisDefinition, { text: 'hello' }, { correlationId: 'corr-1', inputArtifacts: [] });
    expect(result.output).toEqual({ summary: 'echo:hello' });
    expect(result.runId).toContain('corr-1');
    expect(result.modelRun.provider).toBe('fake');
  });

  it('rejects tool budget exhaustion', async () => {
    await expect(new AgentRunner().run({ ...fakeAnalysisDefinition, invoke: async () => ({ output: { summary: 'ok' }, toolCalls: [{ toolId: 'a', input: {}, output: {} }, { toolId: 'b', input: {}, output: {} }] }) }, { text: 'x' }, { correlationId: 'corr-2', inputArtifacts: [] })).rejects.toThrow('budget');
  });
});
