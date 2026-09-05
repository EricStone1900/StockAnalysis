import type { ActivityFailureCategory } from './activity-errors.js';

export interface WorkflowOperationalPolicy {
  workflowTimeoutMinutes: number;
  activityMaximumAttempts: number;
  blockedQueue: string;
  maxOpenApprovals: number;
}

export const DEFAULT_OPERATIONAL_POLICY: WorkflowOperationalPolicy = {
  workflowTimeoutMinutes: 60,
  activityMaximumAttempts: 3,
  blockedQueue: 'workflow-blocked-v1',
  maxOpenApprovals: 100,
};

export function shouldRetryActivity(category: ActivityFailureCategory, attempt: number, policy = DEFAULT_OPERATIONAL_POLICY): boolean {
  return category === 'RETRYABLE' && attempt < policy.activityMaximumAttempts;
}

export function classifyRunbookAction(category: ActivityFailureCategory): 'RETRY' | 'BLOCK_AND_ALERT' | 'CANCEL_AND_AUDIT' | 'FAIL' {
  if (category === 'RETRYABLE') return 'RETRY';
  if (category === 'BLOCKED') return 'BLOCK_AND_ALERT';
  if (category === 'CANCELLED') return 'CANCEL_AND_AUDIT';
  return 'FAIL';
}
