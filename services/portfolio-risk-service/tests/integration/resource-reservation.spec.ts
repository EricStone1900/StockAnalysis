import { randomUUID } from 'node:crypto';
import { readFile } from 'node:fs/promises';
import { Pool } from 'pg';
import { afterAll, beforeAll, describe, expect, it } from 'vitest';
import { PostgresResourceReservationRepository } from '../../src/infrastructure/postgres-resource-reservation-repository.js';
import { reserveResources } from '../../src/domain/resource-reservation.js';

const url = process.env.PORTFOLIO_DATABASE_URL;
const suite = url ? describe : describe.skip;
suite('资源预留PostgreSQL并发', () => {
  const schema = `resource_test_${randomUUID().replaceAll('-', '')}`;
  const pool = new Pool({ connectionString: url, options: `-c search_path=${schema}`, max: 4 });
  const request = (id: string) => ({ reservationId: id, portfolioId: 'p', ledgerVersion: 1, decisionId: 'd', proposalVersion: 1, riskEvaluationId: 'risk', riskPolicyVersion: 'policy', executionContentHash: 'a'.repeat(64), feeBuffer: '1', legs: [{ legId: 'b', securityId: 'SSE:600001', side: 'BUY' as const, quantity: '1', limitPrice: '10' }], idempotencyKey: id });
  beforeAll(async () => {
    await pool.query(`CREATE SCHEMA ${schema}`);
    await pool.query(await readFile(new URL('../../migrations/001_portfolio_ledger.sql', import.meta.url), 'utf8'));
    await pool.query(await readFile(new URL('../../migrations/002_resource_reservations.sql', import.meta.url), 'utf8'));
    const snapshot = { snapshotId: 's', portfolioId: 'p', accountId: 'a', asOf: '2026-09-05T00:00:00Z', cash: '100', positions: [{ securityId: 'SSE:600000', quantity: '10', availableQuantity: '10' }], ledgerVersion: 1, sourceRef: 'test', contentHash: 'x' };
    await pool.query('INSERT INTO portfolio_snapshots (snapshot_id, portfolio_id, account_id, as_of, cash, positions, ledger_version, source_ref, content_hash, payload) VALUES ($1,$2,$3,$4,$5,$6::jsonb,$7,$8,$9,$10::jsonb)', ['s', 'p', 'a', snapshot.asOf, '100', JSON.stringify(snapshot.positions), 1, 'test', 'x', JSON.stringify(snapshot)]);
  });
  afterAll(async () => { await pool.query(`DROP SCHEMA ${schema} CASCADE`); await pool.end(); });
  it('不同进程并发只允许一个活动占用，并且幂等载荷冲突拒绝', async () => {
    const repository = new PostgresResourceReservationRepository(pool);
    const result = await Promise.allSettled(['one', 'two'].map((id) => repository.reserve(request(id), (snapshot, active) => reserveResources(snapshot, active, request(id)))));
    expect(result.filter((item) => item.status === 'fulfilled')).toHaveLength(1);
    expect(result.filter((item) => item.status === 'rejected')).toHaveLength(1);
    const winner = result.find((item): item is PromiseFulfilledResult<Awaited<ReturnType<typeof repository.reserve>>> => item.status === 'fulfilled')!.value;
    await expect(repository.reserve({ ...request(winner.reservationId), executionContentHash: 'b'.repeat(64) }, (snapshot, active) => reserveResources(snapshot, active, { ...request(winner.reservationId), executionContentHash: 'b'.repeat(64) }))).rejects.toThrow('conflict');
  });
  it('UNKNOWN保持占用，SETTLED后才能创建下一笔', async () => {
    const repository = new PostgresResourceReservationRepository(pool);
    const current = (await pool.query<{ reservation_id: string }>('SELECT reservation_id FROM portfolio_resource_reservations LIMIT 1')).rows[0]!.reservation_id;
    await repository.transition(current, 'DISPATCHING'); await repository.transition(current, 'UNKNOWN');
    await expect(repository.reserve(request('blocked'), (snapshot, active) => reserveResources(snapshot, active, request('blocked')))).rejects.toThrow('active');
    await repository.transition(current, 'SETTLED');
    await expect(repository.reserve(request('next'), (snapshot, active) => reserveResources(snapshot, active, request('next')))).resolves.toMatchObject({ status: 'RESERVED' });
  });
});
