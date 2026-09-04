import { describe, expect, it } from 'vitest';
import { FakeStage05Publisher } from '../src/stage05.js';

describe('阶段05三服务契约链路', () => {
  it('贯通 Proposal → Risk → Approval → Execution → Fill', async () => {
    const publisher = new FakeStage05Publisher(); const correlationId = 'stage05-correlation-1';
    await publisher.publish({ eventId: 'proposal-1', subject: 'stock.decision-governance.trade-proposal.created.v1', correlationId, payload: { proposalId: 'proposal-1', proposalVersion: 1 } });
    await publisher.publish({ eventId: 'risk-1', subject: 'stock.portfolio-risk.risk-evaluation.created.v1', correlationId, payload: { portfolioId: 'portfolio-1', portfolioSnapshotId: 'snapshot-1', ledgerVersion: 1, policyVersion: 'policy-v1', verdict: 'PASS' } });
    await publisher.publish({ eventId: 'approval-1', subject: 'stock.decision-governance.approval.decided.v1', correlationId, payload: { proposalId: 'proposal-1', proposalVersion: 1, decision: 'APPROVED', actorId: 'human-1', reason: '通过' } });
    await publisher.publish({ eventId: 'fill-1', subject: 'stock.trade-execution.fill.recorded.v1', correlationId, payload: { fillId: 'fill-1', intentId: 'intent-1', filledQuantity: '10', fillPrice: '12.34' } });
    expect(publisher.events.map((event) => event.subject)).toEqual(['stock.decision-governance.trade-proposal.created.v1', 'stock.portfolio-risk.risk-evaluation.created.v1', 'stock.decision-governance.approval.decided.v1', 'stock.trade-execution.fill.recorded.v1']);
    expect(new Set(publisher.events.map((event) => event.correlationId))).toEqual(new Set([correlationId]));
  });
});
