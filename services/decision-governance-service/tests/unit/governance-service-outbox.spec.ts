import { createHash } from 'node:crypto';
import { describe, expect, it, vi } from 'vitest';
import { GovernanceService } from '../../src/application/governance-service.js';

const makeCommand = () => { const body = { proposalId: 'p-outbox', proposalVersion: 1, kind: 'HOLD' as const, state: 'DRAFT' as const, agentRunId: 'run', targetPortfolioVersion: 1, legs: [], evidence: [], createdAt: '2026-09-04T00:00:00Z' }; return { ...body, contentHash: createHash('sha256').update(JSON.stringify(body)).digest('hex'), idempotencyKey: 'key-outbox', correlationId: 'corr-1' }; };
describe('GovernanceService Outbox binding', () => {
  it('创建、复核和审批分别写入审计事件', async () => {
    const events: unknown[] = []; const outbox = { append: vi.fn(async (event: unknown) => { events.push(event); }) };
    const service = new GovernanceService(undefined, undefined, undefined, undefined, outbox as never);
    const proposal = await service.createDraft(makeCommand()); await service.attachRiskReview(proposal.proposalId, 1, { evaluationId: 'eval-1', policyVersion: 'policy-v1', verdict: 'PASS', reviewedAt: '2026-09-04T00:01:00Z' }); await service.markRiskPassed(proposal.proposalId, 1, 'eval-1'); await service.decide(proposal.proposalId, 1, { actorId: 'human', decision: 'APPROVED', reason: '通过', decidedAt: '2026-09-04T00:02:00Z' });
    expect(events).toHaveLength(3); expect(outbox.append).toHaveBeenCalledTimes(3);
  });
  it('Outbox 写入失败时不静默处理', async () => { const outbox = { append: vi.fn().mockRejectedValue(new Error('outbox unavailable')) }; const service = new GovernanceService(undefined, undefined, undefined, undefined, outbox as never); await expect(service.createDraft(makeCommand())).rejects.toThrow('outbox unavailable'); });
});
