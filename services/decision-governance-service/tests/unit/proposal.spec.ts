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
});
