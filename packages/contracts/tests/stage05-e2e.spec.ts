import { describe, expect, it } from 'vitest';
import { FakeStage05Publisher } from '../src/stage05.js';

describe('阶段05三服务契约链路', () => {
  it('贯通 Proposal → Risk → Approval → Execution → Fill', async () => {
    const publisher = new FakeStage05Publisher(); const correlationId = 'stage05-correlation-1';
    const base = { schemaVersion: 1, occurredAt: '2026-09-04T01:00:00Z', availableAt: '2026-09-04T01:00:00Z', correlationId };
    await publisher.publish({ ...base, eventId: 'proposal-1', subject: 'stock.decision-governance.trade-proposal.created.v1', producer: 'decision-governance-service', payload: { proposalId: 'proposal-1', proposalVersion: 1 } });
    await publisher.publish({ ...base, eventId: 'risk-1', subject: 'stock.portfolio-risk.risk-evaluation.created.v1', producer: 'portfolio-risk-service', payload: { portfolioId: 'portfolio-1', portfolioSnapshotId: 'snapshot-1', ledgerVersion: 1, policyVersion: 'policy-v1', verdict: 'PASS' } });
    await publisher.publish({ ...base, eventId: 'approval-1', subject: 'stock.decision-governance.approval.decided.v1', producer: 'decision-governance-service', payload: { proposalId: 'proposal-1', proposalVersion: 1, decision: 'APPROVED', actorId: 'human-1', reason: '通过' } });
    await publisher.publish({ ...base, eventId: 'fill-1', subject: 'stock.trade-execution.fill.recorded.v1', producer: 'trade-execution-service', payload: { fillId: 'fill-1', intentId: 'intent-1', filledQuantity: '10', fillPrice: '12.34' } });
    expect(publisher.events.map((event) => event.subject)).toEqual(['stock.decision-governance.trade-proposal.created.v1', 'stock.portfolio-risk.risk-evaluation.created.v1', 'stock.decision-governance.approval.decided.v1', 'stock.trade-execution.fill.recorded.v1']);
    expect(new Set(publisher.events.map((event) => event.correlationId))).toEqual(new Set([correlationId]));
  });
});
