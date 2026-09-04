import { BadRequestException } from '@nestjs/common';
import { describe, expect, it, vi } from 'vitest';
import { ReconciliationController } from '../../src/bootstrap/main.js';

describe('ReconciliationController', () => {
  it('requires matching idempotency, actor and correlation headers', async () => {
    const service = { recordConfirmedFill: vi.fn().mockResolvedValue({ ledgerVersion: 2 }), recordCashDividend: vi.fn().mockResolvedValue({ ledgerVersion: 3 }) };
    const controller = new ReconciliationController(service);
    const body = { portfolioId: 'p-1', actorId: 'actor-1', idempotencyKey: 'fill-1' } as never;
    await expect(controller.applyConfirmedFill('fill-1', 'actor-1', 'corr-1', body)).resolves.toEqual({ ledgerVersion: 2 });
    await expect(controller.applyConfirmedFill('other', 'actor-1', 'corr-1', body)).rejects.toBeInstanceOf(BadRequestException);
    await expect(controller.applyCashDividend('dividend-1', 'actor-1', 'corr-1', { portfolioId: 'p-1', actorId: 'actor-1', idempotencyKey: 'dividend-1' } as never)).resolves.toEqual({ ledgerVersion: 3 });
  });
});
