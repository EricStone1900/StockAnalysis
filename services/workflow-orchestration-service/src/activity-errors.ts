export type ActivityFailureCategory = 'RETRYABLE' | 'NON_RETRYABLE' | 'BLOCKED' | 'CANCELLED';

export class WorkflowActivityError extends Error {
  public constructor(public readonly category: ActivityFailureCategory, message: string) { super(message); }
}

export function isRetryable(category: ActivityFailureCategory): boolean { return category === 'RETRYABLE'; }
export function blocksWorkflow(category: ActivityFailureCategory): boolean { return category === 'BLOCKED' || category === 'CANCELLED'; }
