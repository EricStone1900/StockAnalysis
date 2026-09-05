import { describe, expect, it } from 'vitest';
import { ExecutionAuthorizationService } from '../../src/application/execution-authorization-service.js';
import { GovernanceService } from '../../src/application/governance-service.js';
import { createHash } from 'node:crypto';

const hash = 'a'.repeat(64);
const input = { decisionId: 'decision-1', proposalId: 'proposal-1', proposalVersion: 2, budgetReservationId: 'budget-1', resourceReservationId: 'resource-1', executionContentHash: hash, validUntil: '2026-09-06T00:00:00.000Z' } as const;
const proposal = { proposalId: input.proposalId, proposalVersion: input.proposalVersion, kind: 'REBALANCE' as const, state: 'APPROVED' as const, agentRunId: 'run-1', targetPortfolioVersion: 7, legs: [], evidence: [], contentHash: hash, createdAt: '2026-09-05T00:00:00.000Z', riskReview: { evaluationId: 'risk-1', policyVersion: 'policy-1', verdict: 'PASS' as const, reviewedAt: '2026-09-05T00:00:00.000Z' }, approval: { actorId: 'reviewer', decision: 'APPROVED' as const, reason: 'ok', decidedAt: '2026-09-05T00:01:00.000Z' } };
const budget = { reservationId: input.budgetReservationId, portfolioId: 'portfolio-1', tradingDate: '2026-09-05', proposalId: input.proposalId, reason: 'NORMAL', batchNumber: 1, status: 'DISPATCHING' as const };
const resource = { reservationId: input.resourceReservationId, portfolioId: 'portfolio-1', ledgerVersion: 7, decisionId: input.decisionId, proposalVersion: 2, riskEvaluationId: 'risk-1', riskPolicyVersion: 'policy-1', executionContentHash: hash, reservedCash: '100', reservedSells: {}, status: 'DISPATCHING' as const };

describe('ExecutionAuthorizationService', () => {
  it('只在审批、预算和资源占用都完全匹配时发放授权', () => {
    const grant = new ExecutionAuthorizationService().issue(input, proposal, budget, resource, new Date('2026-09-05T00:00:00.000Z'));
    expect(grant).toMatchObject({ decisionId: 'decision-1', resourceReservationId: 'resource-1', targetPortfolioVersion: 7 });
    expect(grant.approvalId).toMatch(/^[a-f0-9]{64}$/);
  });
  it('资源进入未知状态或内容哈希改变后拒绝授权', () => {
    const service = new ExecutionAuthorizationService();
    expect(() => service.issue(input, proposal, budget, { ...resource, status: 'UNKNOWN' }, new Date('2026-09-05T00:00:00.000Z'))).toThrow('resource reservation is not dispatching');
    expect(() => service.issue({ ...input, executionContentHash: 'b'.repeat(64) }, proposal, budget, resource, new Date('2026-09-05T00:00:00.000Z'))).toThrow('execution authority references do not match');
  });
  it('治理服务只从已迁移到 DISPATCHING 的预算发放授权', async () => {
    const service = new GovernanceService();
    const draft = { proposalId: 'proposal-issued', proposalVersion: 1, kind: 'REBALANCE' as const, state: 'DRAFT' as const, agentRunId: 'run', targetPortfolioVersion: 7, legs: [{ securityId: '000001.SZ', side: 'BUY' as const, quantity: '1' }], evidence: [], createdAt: '2026-09-05T00:00:00.000Z' };
    const proposal = await service.createDraft({ ...draft, contentHash: createHash('sha256').update(JSON.stringify(draft)).digest('hex'), idempotencyKey: 'proposal-issued-key' });
    await service.attachRiskReview(proposal.proposalId, 1, { evaluationId: 'risk-1', policyVersion: 'policy-1', verdict: 'PASS', reviewedAt: '2026-09-05T00:00:00.000Z' });
    await service.markRiskPassed(proposal.proposalId, 1, 'risk-1');
    await service.decide(proposal.proposalId, 1, { actorId: 'reviewer', decision: 'APPROVED', reason: 'ok', decidedAt: '2026-09-05T00:01:00.000Z' });
    await service.reserveBudget({ reservationId: 'budget-issued', portfolioId: 'portfolio-1', tradingDate: '2026-09-05', reason: 'NORMAL', proposalId: proposal.proposalId, kind: 'REBALANCE', idempotencyKey: 'budget-issued-key' }, { maxDailyRebalanceBatches: 1, allowedSecondBatchReasons: [] });
    await expect(service.issueExecutionAuthorization({ ...input, decisionId: 'decision-issued', proposalId: proposal.proposalId, proposalVersion: 1, budgetReservationId: 'budget-issued' }, { ...resource, decisionId: 'decision-issued', proposalVersion: 1 }, new Date('2026-09-05T00:00:00.000Z'))).rejects.toThrow('budget reservation is not dispatching');
    await service.markBudgetDispatching('budget-issued');
    await expect(service.issueExecutionAuthorization({ ...input, decisionId: 'decision-issued', proposalId: proposal.proposalId, proposalVersion: 1, budgetReservationId: 'budget-issued' }, { ...resource, decisionId: 'decision-issued', proposalVersion: 1 }, new Date('2026-09-05T00:00:00.000Z'))).resolves.toMatchObject({ budgetReservationId: 'budget-issued' });
  });
});
