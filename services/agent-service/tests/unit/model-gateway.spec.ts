import { describe, expect, it } from 'vitest';
import { FakeModelProvider, ModelGateway } from '../../src/application/model-gateway.js';

const capabilities = { structuredOutput: true, toolCalling: true, maxContextTokens: 16_000 };
const response = { text: '{"summary":"ok"}', inputTokens: 10, outputTokens: 5, costUsd: 0.01 };
const request = { prompt: 'fixture', requireStructuredOutput: true, requireToolCalling: true, maxCostUsd: 1 };

describe('model gateway', () => {
  it('falls back to the next compatible provider and records provider identity', async () => {
    const primary = new FakeModelProvider('primary', response, capabilities, new Error('timeout'));
    const fallback = new FakeModelProvider('fallback', response, capabilities);
    const run = await new ModelGateway([primary, fallback]).invoke({ id: 'reasoning', providers: ['primary', 'fallback'] }, request);
    expect(run.providerId).toBe('fallback');
    expect(run.modelRunId).toContain('fallback');
  });

  it('rejects unsupported capabilities and cost budget breaches', async () => {
    const noTools = new FakeModelProvider('no-tools', response, { ...capabilities, toolCalling: false });
    const expensive = new FakeModelProvider('expensive', { ...response, costUsd: 2 }, capabilities);
    await expect(new ModelGateway([noTools, expensive]).invoke({ id: 'p', providers: ['no-tools', 'expensive'] }, request)).rejects.toThrow('all model providers failed');
  });
});
