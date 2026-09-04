import { BadRequestException, ConflictException, NotFoundException } from '@nestjs/common';
import { describe, expect, it, vi } from 'vitest';
import { PortfolioController } from '../../src/bootstrap/main.js';

const snapshot = { snapshotId: 's-1' } as never;
describe('PortfolioController API mapping', () => {
  it('returns a snapshot and maps missing data to 404', async () => {
    const service = { importOpening: vi.fn().mockResolvedValue(snapshot), latest: vi.fn().mockResolvedValueOnce(snapshot).mockResolvedValueOnce(undefined) };
    const controller = new PortfolioController(service);
    await expect(controller.importOpening('p-1', 'key-1', 'actor-1', 'corr-1', { idempotencyKey: 'key-1', actorId: 'actor-1' } as never)).resolves.toEqual(snapshot);
    await expect(controller.latest('p-1')).resolves.toEqual(snapshot);
    await expect(controller.latest('p-1')).rejects.toBeInstanceOf(NotFoundException);
  });

  it('maps version conflicts to 409 and validation errors to 400', async () => {
    const service = { importOpening: vi.fn().mockRejectedValueOnce(new Error('ledger version conflict')).mockRejectedValueOnce(new Error('invalid event time')), latest: vi.fn() };
    const controller = new PortfolioController(service);
    await expect(controller.importOpening('p-1', 'key', 'actor', 'corr', { idempotencyKey: 'key', actorId: 'actor' } as never)).rejects.toBeInstanceOf(ConflictException);
    await expect(controller.importOpening('p-1', 'key', 'actor', 'corr', { idempotencyKey: 'other', actorId: 'actor' } as never)).rejects.toBeInstanceOf(BadRequestException);
  });

  it('exposes the reversal endpoint with idempotency validation', async () => {
    const service = { importOpening: vi.fn(), latest: vi.fn(), reverse: vi.fn().mockResolvedValue({ type: 'REVERSAL' }) };
    const controller = new PortfolioController(service);
    await expect(controller.reverse('p-1', 'entry-1', 'reverse-key', 'actor', 'corr', { idempotencyKey: 'reverse-key', actorId: 'actor' } as never)).resolves.toEqual({ type: 'REVERSAL' });
    await expect(controller.reverse('p-1', 'entry-1', 'wrong', 'actor', 'corr', { idempotencyKey: 'reverse-key', actorId: 'actor' } as never)).rejects.toBeInstanceOf(BadRequestException);
  });

  it('exposes the risk evaluation endpoint', async () => {
    const evaluation = { evaluationId: 'risk-1', verdict: 'PASS' };
    const service = { importOpening: vi.fn(), latest: vi.fn(), evaluateRisk: vi.fn().mockResolvedValue(evaluation) };
    const controller = new PortfolioController(service);
    await expect(controller.evaluateRisk('p-1', { proposalId: 'proposal-1', reason: 'NORMAL', legs: [], prices: {}, decisionBudget: { rebalanceBatchesToday: 0 }, peakEquity: '100', policy: {} as never })).resolves.toEqual(evaluation);
  });
});
