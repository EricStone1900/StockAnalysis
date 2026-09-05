import type { ActivityRequest, ActivityResponse, ArtifactRef } from '../activities/activity-contract.js';

export interface HumanApprovalPayload { decisionId: string; proposalVersion: number; expiresAt: string; }
export type HumanApprovalRequest = ActivityRequest<HumanApprovalPayload>;
export type ApprovalAction = 'APPROVE' | 'REJECT' | 'MODIFY' | 'REFRESH';
export interface ApprovalSignal { action: ApprovalAction; reason: string; idempotencyKey: string; }
export interface HumanApprovalStepResult { artifactRef: ArtifactRef; recorded?: boolean; }
export interface HumanApprovalActivities {
  loadApprovalBundle(request: HumanApprovalRequest): Promise<ActivityResponse<HumanApprovalStepResult>>;
  recordApproval(request: HumanApprovalRequest & { payload: HumanApprovalPayload & { action: ApprovalAction; reason: string } }): Promise<ActivityResponse<HumanApprovalStepResult>>;
  refreshApprovalBundle(request: HumanApprovalRequest): Promise<ActivityResponse<HumanApprovalStepResult>>;
}
export type HumanApprovalStatus = 'APPROVED' | 'REJECTED' | 'MODIFICATION_REQUIRED' | 'REFRESH_REQUIRED' | 'EXPIRED';
export interface HumanApprovalWorkflowResult { status: HumanApprovalStatus; artifactRefs: readonly ArtifactRef[]; }

export function validateApprovalSignal(signal: ApprovalSignal): ApprovalSignal {
  if (!signal.reason.trim() || !signal.idempotencyKey.trim()) throw new Error('approval signal requires reason and idempotency key');
  return signal;
}

export function buildApprovalRequest(request: HumanApprovalRequest, signal: ApprovalSignal): HumanApprovalRequest & { payload: HumanApprovalPayload & { action: ApprovalAction; reason: string } } {
  validateApprovalSignal(signal);
  return { ...request, idempotencyKey: signal.idempotencyKey, payload: { ...request.payload, action: signal.action, reason: signal.reason } };
}
