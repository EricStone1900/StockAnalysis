import { describe, expect, it } from 'vitest';
import { FakeHumanApprovalActivities } from '../../src/activities/fake-activities.js';
import { buildApprovalRequest, validateApprovalSignal, type HumanApprovalRequest } from '../../src/workflows/human-approval.contract.js';

const request: HumanApprovalRequest = { workflowId: 'approval-1', runId: 'run-1', correlationId: 'corr-approval-1', idempotencyKey: 'approval-1', payload: { decisionId: 'decision-1', proposalVersion: 1, expiresAt: '2026-09-05T16:00:00Z' } };

describe('HumanApprovalWorkflow contract', () => {
  it('requires reason and idempotency key for every human signal', () => {
    expect(validateApprovalSignal({ action: 'APPROVE', reason: 'reviewed', idempotencyKey: 'approve-1' }).action).toBe('APPROVE');
    expect(() => validateApprovalSignal({ action: 'REJECT', reason: '', idempotencyKey: 'reject-1' })).toThrow('reason');
  });

  it('records approval actions idempotently without creating orders', async () => {
    const activities = new FakeHumanApprovalActivities();
    const bundle = await activities.loadApprovalBundle(request);
    const approvalRequest = buildApprovalRequest(request, { action: 'APPROVE', reason: '人工确认风险评估', idempotencyKey: 'approve-1' });
    const first = await activities.recordApproval(approvalRequest);
    const replay = await activities.recordApproval(approvalRequest);
    expect(first).toEqual(replay);
    expect(bundle.result.artifactRef.uri).toContain('approval-bundle');
    expect(first.result.artifactRef.uri).toContain('approval-record');
  });

  it('uses a distinct refresh signal and never treats refresh as approval', () => {
    const refresh = buildApprovalRequest(request, { action: 'REFRESH', reason: '证据已过期，要求刷新', idempotencyKey: 'refresh-1' });
    expect(refresh.payload.action).toBe('REFRESH');
    expect(refresh.payload.action).not.toBe('APPROVE');
  });
});
