import { createHash } from 'node:crypto';
import { describe, expect, it } from 'vitest';
import { GrantExecutionAuthorization } from '../../src/application/execution-authorization.js';
const command = () => { const base = { rebalanceBatchId: 'b', decisionId: 'd', proposalVersion: 2, approvalId: 'a', riskEvaluationId: 'r', budgetReservationId: 'budget', resourceReservationId: 'resource', targetPortfolioVersion: 3, validUntil: '2099-01-01T00:00:00Z', legs: [{ legId: 'l', securityId: 's', side: 'BUY' as const, quantity: '1' }] }; return { ...base, contentHash: createHash('sha256').update(JSON.stringify(base)).digest('hex'), idempotencyKey: 'k' }; };
describe('权威执行授权', () => {
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
