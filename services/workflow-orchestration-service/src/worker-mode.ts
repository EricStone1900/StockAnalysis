export function assertDemoWorkerMode(env: Readonly<Record<string, string | undefined>>): void {
  if (env.WORKFLOW_RUNTIME_MODE !== 'demo' || env.NODE_ENV === 'production') {
    throw new Error('Only explicit demo Worker is available; real activity adapters are not configured');
  }
  if (env.WORKFLOW_EXECUTION_ENABLED !== 'false') {
    throw new Error('Demo Worker requires WORKFLOW_EXECUTION_ENABLED=false');
  }
}
