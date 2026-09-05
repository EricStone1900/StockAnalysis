import { describe, expect, it } from 'vitest';
import { contextHash, PromptRegistry, RunMemoryM0, stringTool, ToolRegistry } from '../../src/application/registries.js';

describe('agent registries', () => {
  it('fails closed for unapproved prompts and unauthorized or side-effect tools', async () => {
    const registry = new ToolRegistry([stringTool('read'), stringTool('write', true)]);
    const policy = { agentId: 'fake', allowedTools: ['read', 'write'], maxCalls: 1, denySideEffects: true };
    await expect(registry.call(policy, 'missing', { value: 'x' })).rejects.toThrow('authorized');
    await expect(registry.call(policy, 'write', { value: 'x' })).rejects.toThrow('side-effect');
    const prompts = new PromptRegistry([{ agentId: 'fake', agentVersion: 'v1', promptVersion: 'p1', template: 'system', status: 'DRAFT' }]);
    expect(() => prompts.get('fake', 'v1')).toThrow('approved');
  });

  it('produces stable context hashes and keeps M0 memory only per run', () => {
    const refs = [{ id: 'e2', freshness: 'FRESH' as const, untrusted: true }, { id: 'e1', freshness: 'STALE' as const, untrusted: false }];
    expect(contextHash(refs)).toBe(contextHash([...refs].reverse()));
    expect(() => contextHash([{ id: 'future', freshness: 'FUTURE', untrusted: true }])).toThrow('future');
    const memory = new RunMemoryM0(); memory.put('run-1', { value: 1 }); memory.clear('run-1');
    expect(memory.get('run-1')).toBeUndefined();
  });
});
