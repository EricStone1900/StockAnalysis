import { describe, expect, it } from 'vitest';
import { approvalDecidedEvent, proposalCreatedEvent, riskReviewedEvent } from '../../src/domain/governance-events.js';

const proposal = { proposalId: 'p-1', proposalVersion: 1, state: 'DRAFT', contentHash: 'a'.repeat(64) } as never;
describe('Governance 审计事件', () => {
  it('生成 Proposal 创建事件', () => { const event = proposalCreatedEvent(proposal, 'corr-1', '2026-09-04T00:00:00Z'); expect(event.subject).toBe('stock.decision-governance.trade-proposal.created.v1'); expect(event.payload).toMatchObject({ proposalId: 'p-1', proposalVersion: 1 }); });
  it('包含风险复核和审批关键信息', () => { const review = riskReviewedEvent(proposal, { evaluationId: 'eval-1', policyVersion: 'policy-v1', verdict: 'PASS', reviewedAt: '2026-09-04T00:00:00Z' }, 'corr-1', '2026-09-04T00:00:00Z'); const approval = approvalDecidedEvent(proposal, { actorId: 'human-1', decision: 'APPROVED', reason: '通过', decidedAt: '2026-09-04T00:00:00Z' }, 'corr-1', '2026-09-04T00:00:00Z'); expect(review.payload).toMatchObject({ evaluationId: 'eval-1', policyVersion: 'policy-v1' }); expect(approval.payload).toMatchObject({ actorId: 'human-1', decision: 'APPROVED' }); });
});
