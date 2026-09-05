import { describe, expect, it } from 'vitest';
import { readAgentDeployment } from '../../src/application/deployment-config.js';

describe('agent deployment configuration', () => {
  it('requires a single approved Agent ID with isolated consumer and task queue', () => {
    const config = readAgentDeployment({ AGENT_ID: 'risk-review', AGENT_ALLOWED_TOOLS: 'risk.read' });
    expect(config.taskQueue).toContain('risk-review');
    expect(config.allowedTools).toEqual(['risk.read']);
    expect(() => readAgentDeployment({ AGENT_ID: 'unknown' })).toThrow('approved');
    expect(() => readAgentDeployment({ AGENT_ID: 'risk-review', AGENT_TASK_QUEUE: 'shared' })).toThrow('isolated');
  });
});
