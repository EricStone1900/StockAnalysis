export interface WorkflowFeatureFlags {
  globalPaused: boolean;
  observeOnly: boolean;
  agentEnabled: boolean;
  executionEnabled: boolean;
}

export interface WorkflowGateInput { requiresAgent: boolean; requiresExecution: boolean; }
export interface WorkflowGateResult { allowed: boolean; blockedReasons: readonly string[]; }

export const DEFAULT_WORKFLOW_FLAGS: WorkflowFeatureFlags = {
  globalPaused: false,
  observeOnly: true,
  agentEnabled: false,
  executionEnabled: false,
};

export function evaluateWorkflowGate(flags: WorkflowFeatureFlags, input: WorkflowGateInput): WorkflowGateResult {
  const blockedReasons: string[] = [];
  if (flags.globalPaused) blockedReasons.push('GLOBAL_PAUSED');
  if (flags.observeOnly && input.requiresExecution) blockedReasons.push('OBSERVE_ONLY');
  if (input.requiresAgent && !flags.agentEnabled) blockedReasons.push('AGENT_DISABLED');
  if (input.requiresExecution && !flags.executionEnabled) blockedReasons.push('EXECUTION_DISABLED');
  return { allowed: blockedReasons.length === 0, blockedReasons };
}

export function readWorkflowFlags(env: Record<string, string | undefined>): WorkflowFeatureFlags {
  const bool = (name: string, fallback: boolean): boolean => env[name] === undefined ? fallback : env[name] === 'true';
  return {
    globalPaused: bool('WORKFLOW_GLOBAL_PAUSED', DEFAULT_WORKFLOW_FLAGS.globalPaused),
    observeOnly: bool('WORKFLOW_OBSERVE_ONLY', DEFAULT_WORKFLOW_FLAGS.observeOnly),
    agentEnabled: bool('WORKFLOW_AGENT_ENABLED', DEFAULT_WORKFLOW_FLAGS.agentEnabled),
    executionEnabled: bool('WORKFLOW_EXECUTION_ENABLED', DEFAULT_WORKFLOW_FLAGS.executionEnabled),
  };
}
