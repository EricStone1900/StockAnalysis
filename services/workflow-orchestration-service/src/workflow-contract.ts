export const WORKFLOW_TASK_QUEUE = 'stock-workflows-v1';

export const ACTIVITY_RETRY_POLICY = {
  initialInterval: '1 second',
  backoffCoefficient: 2,
  maximumAttempts: 3,
} as const;
