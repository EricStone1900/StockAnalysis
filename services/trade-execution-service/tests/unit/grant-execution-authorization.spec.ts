import { createHash } from 'node:crypto';
import { describe, expect, it, vi } from 'vitest';
import { GrantExecutionAuthorization, HttpExecutionAuthorizationGrantReader } from '../../src/application/execution-authorization.js';
const command = () => { const base = { rebalanceBatchId: 'b', decisionId: 'd', proposalId: 'proposal', proposalVersion: 2, approvalId: 'a', riskEvaluationId: 'r', budgetReservationId: 'budget', resourceReservationId: 'resource', targetPortfolioVersion: 3, validUntil: '2099-01-01T00:00:00Z', legs: [{ legId: 'l', securityId: 's', side: 'BUY' as const, quantity: '1' }] }; return { ...base, contentHash: createHash('sha256').update(JSON.stringify(base)).digest('hex'), idempotencyKey: 'k' }; };
describe('权威执行授权', () => {
  it('通过受服务身份保护的治理 HTTP 端点读取授权', async () => {
    const input = command();
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ decisionId: input.decisionId, proposalVersion: input.proposalVersion, approvalId: input.approvalId, riskEvaluationId: input.riskEvaluationId, budgetReservationId: input.budgetReservationId, resourceReservationId: input.resourceReservationId, targetPortfolioVersion: input.targetPortfolioVersion, executionContentHash: input.contentHash, validUntil: input.validUntil }), { status: 200, headers: { 'content-type': 'application/json' } }));
    vi.stubGlobal('fetch', fetchMock);
    await expect(new HttpExecutionAuthorizationGrantReader('http://governance:3000/', 'governance-token').getGrant(input)).resolves.toMatchObject({ executionContentHash: input.contentHash });
    expect(fetchMock).toHaveBeenCalledWith('http://governance:3000/internal/v1/execution-authorizations', expect.objectContaining({ method: 'POST', headers: { 'content-type': 'application/json', 'x-service-token': 'governance-token' } }));
    vi.unstubAllGlobals();
  });

  it('治理端点拒绝或不可用时不伪造授权', async () => {
    const input = command();
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('', { status: 401 })));
    await expect(new HttpExecutionAuthorizationGrantReader('http://governance:3000', 'wrong-token').getGrant(input)).rejects.toThrow('returned 401');
    vi.unstubAllGlobals();
  });

  it('所有绑定字段一致才允许', async () => {
    const input = command(); const grant = { decisionId: input.decisionId, proposalVersion: input.proposalVersion, approvalId: input.approvalId, riskEvaluationId: input.riskEvaluationId, budgetReservationId: input.budgetReservationId, resourceReservationId: input.resourceReservationId!, targetPortfolioVersion: input.targetPortfolioVersion, executionContentHash: input.contentHash, validUntil: input.validUntil };
    await expect(new GrantExecutionAuthorization({ getGrant: async () => grant }).assertAuthorized(input)).resolves.toBeUndefined();
    await expect(new GrantExecutionAuthorization({ getGrant: async () => ({ ...grant, proposalVersion: 1 }) }).assertAuthorized(input)).rejects.toThrow('does not match');
  });
  it('缺失资源、过期或没有Grant拒绝', async () => {
    const input = command();
    await expect(new GrantExecutionAuthorization({ getGrant: async () => undefined }).assertAuthorized(input)).rejects.toThrow('absent');
    await expect(new GrantExecutionAuthorization({ getGrant: async () => ({ decisionId: 'd', proposalVersion: 2, approvalId: 'a', riskEvaluationId: 'r', budgetReservationId: 'budget', resourceReservationId: 'resource', targetPortfolioVersion: 3, executionContentHash: input.contentHash, validUntil: '2020-01-01T00:00:00Z' }) }).assertAuthorized(input)).rejects.toThrow('expired');
    await expect(new GrantExecutionAuthorization({ getGrant: async () => undefined }).assertAuthorized({ ...input, resourceReservationId: undefined })).rejects.toThrow('resource');
  });
});
