import { describe, expect, it, vi } from 'vitest';
import { PostgresProposalRepository } from '../../src/infrastructure/postgres-proposal-repository.js';

describe('PostgresProposalRepository', () => {
  it('使用参数化 SQL 保存不可变 Proposal', async () => {
    const query = vi.fn().mockResolvedValue({ rows: [] }); const repository = new PostgresProposalRepository({ query });
    const proposal = { proposalId: 'p-1', proposalVersion: 1, kind: 'HOLD' as const, state: 'DRAFT' as const, agentRunId: 'run', targetPortfolioVersion: 1, legs: [], evidence: [], contentHash: 'a'.repeat(64), createdAt: '2026-09-04T00:00:00Z' };
    await repository.append({ ...proposal, idempotencyKey: 'key' }, proposal);
    expect(query).toHaveBeenCalledWith(expect.stringContaining('INSERT INTO trade_proposals'), expect.arrayContaining(['p-1', 1, 'key']));
  });
  it('读取幂等记录和最新版本', async () => { const payload = { proposalId: 'p-1', proposalVersion: 1 } as never; const query = vi.fn().mockResolvedValue({ rows: [{ payload }] }); const repository = new PostgresProposalRepository({ query }); expect(await repository.findByIdempotency('key')).toBe(payload); expect(await repository.latest('p-1')).toBe(payload); });
  it('更新风险复核字段和状态', async () => { const query = vi.fn().mockResolvedValue({ rows: [] }); await new PostgresProposalRepository({ query }).updateRiskReview('p-1', 1, { evaluationId: 'eval-1', policyVersion: 'policy-v1', verdict: 'PASS', reviewedAt: '2026-09-04T00:00:00Z' }, 'RISK_PASSED'); expect(query).toHaveBeenCalledWith(expect.stringContaining('risk_review'), expect.arrayContaining(['RISK_PASSED', 'p-1', 1])); });
});
