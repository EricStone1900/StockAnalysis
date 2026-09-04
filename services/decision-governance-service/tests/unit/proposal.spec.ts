import { createHash } from 'node:crypto';
import { describe, expect, it } from 'vitest';
import { ProposalAggregate } from '../../src/domain/proposal.js';

const hash = (value: unknown) => createHash('sha256').update(JSON.stringify(value)).digest('hex');
describe('ProposalAggregate', () => {
  it('创建可审计的 DRAFT 并按幂等键复用', () => {
    const aggregate = new ProposalAggregate();
    const base = { proposalId: 'p-1', proposalVersion: 1, kind: 'REBALANCE' as const, state: 'DRAFT' as const, agentRunId: 'run-1', targetPortfolioVersion: 1, legs: [{ securityId: 'SSE:600000', side: 'BUY' as const, quantity: '10' }], evidence: [{ kind: 'quant' as const, uri: 'artifact://quant/1', contentHash: 'a'.repeat(64), capturedAt: '2026-09-04T00:00:00Z' }], createdAt: '2026-09-04T00:00:00Z' };
    const command = { ...base, contentHash: hash(base), idempotencyKey: 'key-1' };
    expect(aggregate.createDraft(command)).toEqual(aggregate.createDraft(command));
  });
  it('拒绝非法 HOLD、缺证据哈希和篡改内容', () => {
    const aggregate = new ProposalAggregate();
    expect(() => aggregate.createDraft({ proposalId: 'p', kind: 'HOLD', legs: [{ securityId: 'x', side: 'BUY', quantity: '1' }], agentRunId: 'r', targetPortfolioVersion: 1, evidence: [], contentHash: 'x', idempotencyKey: 'k', createdAt: '2026-09-04T00:00:00Z' })).toThrow('HOLD');
  });

  it('仅允许匹配的 PASS RiskEvaluation 推进状态', () => {
    const aggregate = new ProposalAggregate(); const base = { proposalId: 'p-risk', proposalVersion: 1, kind: 'HOLD' as const, state: 'DRAFT' as const, agentRunId: 'run', targetPortfolioVersion: 1, legs: [], evidence: [], createdAt: '2026-09-04T00:00:00Z' }; const command = { ...base, contentHash: hash(base), idempotencyKey: 'risk-key' };
    aggregate.createDraft(command);
    expect(() => aggregate.markRiskPassed('p-risk', 1, 'eval-1')).toThrow();
    aggregate.attachRiskReview('p-risk', 1, { evaluationId: 'eval-1', policyVersion: 'policy-v1', verdict: 'PASS', reviewedAt: '2026-09-04T00:01:00Z' });
    expect(aggregate.markRiskPassed('p-risk', 1, 'eval-1').state).toBe('RISK_PASSED');
  });

  it('修订生成新版本且不复用旧复核和审批', () => {
    const aggregate = new ProposalAggregate();
    const firstBase = { proposalId: 'p-revise', proposalVersion: 1, kind: 'HOLD' as const, state: 'DRAFT' as const, agentRunId: 'run', targetPortfolioVersion: 1, legs: [], evidence: [], createdAt: '2026-09-04T00:00:00Z' };
    aggregate.createDraft({ ...firstBase, contentHash: hash(firstBase), idempotencyKey: 'rev-1' });
    aggregate.attachRiskReview('p-revise', 1, { evaluationId: 'eval-1', policyVersion: 'policy-v1', verdict: 'PASS', reviewedAt: '2026-09-04T00:01:00Z' });
    aggregate.markRiskPassed('p-revise', 1, 'eval-1');
    const secondBase = { proposalId: 'p-revise', proposalVersion: 2, parentProposalVersion: 1, kind: 'HOLD' as const, state: 'DRAFT' as const, agentRunId: 'run-2', targetPortfolioVersion: 1, legs: [], evidence: [], createdAt: '2026-09-04T00:00:00Z' };
    const second = aggregate.createDraft({ ...secondBase, contentHash: hash(secondBase), idempotencyKey: 'rev-2' });
    expect(second).toMatchObject({ proposalVersion: 2, parentProposalVersion: 1, state: 'DRAFT' });
    expect(second.riskReview).toBeUndefined();
    expect(aggregate.get('p-revise', 1)?.state).toBe('RISK_PASSED');
  });
});
