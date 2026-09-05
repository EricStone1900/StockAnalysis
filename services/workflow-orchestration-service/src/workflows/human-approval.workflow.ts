import { condition, defineSignal, proxyActivities, setHandler } from '@temporalio/workflow';
import { ACTIVITY_RETRY_POLICY } from '../workflow-contract.js';
import { buildApprovalRequest, type ApprovalSignal, type HumanApprovalActivities, type HumanApprovalRequest, type HumanApprovalStatus } from './human-approval.contract.js';

export const approvalSignal = defineSignal<[ApprovalSignal]>('approval');
const activities = proxyActivities<HumanApprovalActivities>({ startToCloseTimeout: '5 minutes', retry: ACTIVITY_RETRY_POLICY });

export async function humanApprovalWorkflow(request: HumanApprovalRequest) {
  const bundle = await activities.loadApprovalBundle(request);
  let signal: ApprovalSignal | undefined;
  setHandler(approvalSignal, (received) => { if (!signal) signal = received; });
  const received = await condition(() => signal !== undefined, '24 hours');
  if (!received || !signal) return { status: 'EXPIRED' as HumanApprovalStatus, artifactRefs: [bundle.result.artifactRef] };
  const approvalRequest = buildApprovalRequest(request, signal);
  if (signal.action === 'REFRESH') {
    const refreshed = await activities.refreshApprovalBundle(request);
    return { status: 'REFRESH_REQUIRED' as HumanApprovalStatus, artifactRefs: [bundle.result.artifactRef, refreshed.result.artifactRef] };
  }
  const recorded = await activities.recordApproval(approvalRequest);
  const status: HumanApprovalStatus = signal.action === 'APPROVE' ? 'APPROVED' : signal.action === 'REJECT' ? 'REJECTED' : 'MODIFICATION_REQUIRED';
  return { status, artifactRefs: [bundle.result.artifactRef, recorded.result.artifactRef] };
}
