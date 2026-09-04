import { BadRequestException, NotFoundException } from '@nestjs/common';
import { createHash } from 'node:crypto';
import { describe, expect, it } from 'vitest';
import { ProposalController } from '../../src/bootstrap/main.js';

const base = { proposalId: 'p-1', proposalVersion: 1, kind: 'HOLD' as const, state: 'DRAFT' as const, agentRunId: 'run-1', targetPortfolioVersion: 1, legs: [], evidence: [], createdAt: '2026-09-04T00:00:00Z' };
describe('ProposalController', () => {
  it('创建并读取 DRAFT Proposal', async () => {
    const controller = new ProposalController(); const command = { ...base, contentHash: createHash('sha256').update(JSON.stringify(base)).digest('hex'), idempotencyKey: 'key-1' };
    const created = controller.create(command); expect(created.state).toBe('DRAFT'); expect(controller.get('p-1')).toEqual(created);
  });
  it('映射非法请求和不存在 Proposal', () => { const controller = new ProposalController(); expect(() => controller.create({ ...base, contentHash: 'bad', idempotencyKey: 'key-2' })).toThrow(BadRequestException); expect(() => controller.get('missing')).toThrow(NotFoundException); });
});
