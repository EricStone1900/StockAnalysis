import { describe, expect, it } from 'vitest';
import { FakeWorkflowActivities } from '../../src/activities/fake-activities.js';

const request = { workflowId: 'workflow-1', runId: 'run-1', correlationId: 'corr-1', idempotencyKey: 'key-1', payload: { dependency: 'market-data-service' } };

describe('FakeWorkflowActivities', () => {
  it('requires full activity identifiers and reuses the idempotent result', async () => {
    const activities = new FakeWorkflowActivities();
    const first = await activities.verifyDependency(request);
    const replay = await activities.verifyDependency({ ...request, runId: 'run-2' });
    expect(first).toEqual(replay);
    expect(first.result).toEqual({ status: 'UP', dependency: 'market-data-service' });
  });

  it('rejects activities without an idempotency key', async () => {
    await expect(new FakeWorkflowActivities().verifyDependency({ ...request, idempotencyKey: '' })).rejects.toThrow('idempotency');
  });
});
