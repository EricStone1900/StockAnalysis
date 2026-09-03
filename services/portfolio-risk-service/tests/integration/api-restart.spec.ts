import { readFile } from 'node:fs/promises';
import { Pool } from 'pg';
import { NestFactory } from '@nestjs/core';
import { FastifyAdapter } from '@nestjs/platform-fastify';
import { afterAll, beforeAll, describe, expect, it } from 'vitest';
import { AppModule } from '../../src/bootstrap/main.js';

const databaseUrl = process.env.PORTFOLIO_DATABASE_URL;
const suite = databaseUrl ? describe : describe.skip;
suite('Portfolio API restart recovery', () => {
  const pool = new Pool({ connectionString: databaseUrl });
  const portfolioId = `api-restart-${Date.now()}`;
  beforeAll(async () => { await pool.query(await readFile(new URL('../../migrations/001_portfolio_ledger.sql', import.meta.url), 'utf8')); });
  afterAll(async () => { await pool.query('DELETE FROM portfolio_snapshot_idempotency WHERE portfolio_id = $1', [portfolioId]); await pool.query('DELETE FROM portfolio_snapshots WHERE portfolio_id = $1', [portfolioId]); await pool.query('DELETE FROM portfolio_ledger_entries WHERE portfolio_id = $1', [portfolioId]); await pool.end(); });

  it('continues versioned writes after recreating the Nest application', async () => {
    const body = { accountId: 'account-api', cash: '10.00', positions: [], occurredAt: '2026-09-03T00:00:00Z', availableAt: '2026-09-03T00:00:00Z', sourceRef: 'api-restart', actorId: 'test', reason: '测试', expectedVersion: 0, idempotencyKey: 'api-restart-key-1' };
    const firstApp = await NestFactory.create(AppModule, new FastifyAdapter()); await firstApp.init();
    const first = await firstApp.getHttpAdapter().getInstance().inject({ method: 'POST', url: `/api/v1/portfolios/${portfolioId}/manual-snapshots`, headers: { 'Idempotency-Key': body.idempotencyKey, 'X-Actor-Id': body.actorId, 'X-Correlation-Id': 'corr-1' }, payload: body });
    expect(first.statusCode).toBe(201); await firstApp.close();
    const secondApp = await NestFactory.create(AppModule, new FastifyAdapter()); await secondApp.init();
    const second = await secondApp.getHttpAdapter().getInstance().inject({ method: 'POST', url: `/api/v1/portfolios/${portfolioId}/manual-snapshots`, headers: { 'Idempotency-Key': 'api-restart-key-2', 'X-Actor-Id': body.actorId, 'X-Correlation-Id': 'corr-2' }, payload: { ...body, expectedVersion: 1, idempotencyKey: 'api-restart-key-2' } });
    expect(second.statusCode).toBe(201); expect(second.json().ledgerVersion).toBe(2); await secondApp.close();
  });
});
