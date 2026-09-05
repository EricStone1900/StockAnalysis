import { describe, expect, it } from 'vitest';
import { DEFAULT_WORKFLOW_FLAGS, evaluateWorkflowGate, readWorkflowFlags } from '../../src/reliability-policy.js';
import { classifyRunbookAction, shouldRetryActivity } from '../../src/operations-policy.js';

describe('workflow reliability policy', () => {
  it('defaults to observe-only with agents and execution disabled', () => {
    expect(evaluateWorkflowGate(DEFAULT_WORKFLOW_FLAGS, { requiresAgent: true, requiresExecution: true })).toEqual({ allowed: false, blockedReasons: ['OBSERVE_ONLY', 'AGENT_DISABLED', 'EXECUTION_DISABLED'] });
  });

  it('global pause blocks every workflow and flags are explicit booleans', () => {
    const flags = readWorkflowFlags({ WORKFLOW_GLOBAL_PAUSED: 'true', WORKFLOW_OBSERVE_ONLY: 'false', WORKFLOW_AGENT_ENABLED: 'true', WORKFLOW_EXECUTION_ENABLED: 'true' });
    expect(evaluateWorkflowGate(flags, { requiresAgent: false, requiresExecution: false })).toEqual({ allowed: false, blockedReasons: ['GLOBAL_PAUSED'] });
  });

  it('retries only retryable failures before the attempt limit', () => {
    expect(shouldRetryActivity('RETRYABLE', 1)).toBe(true);
    expect(shouldRetryActivity('RETRYABLE', 3)).toBe(false);
    expect(shouldRetryActivity('BLOCKED', 1)).toBe(false);
    expect(classifyRunbookAction('BLOCKED')).toBe('BLOCK_AND_ALERT');
    expect(classifyRunbookAction('CANCELLED')).toBe('CANCEL_AND_AUDIT');
  });
});
