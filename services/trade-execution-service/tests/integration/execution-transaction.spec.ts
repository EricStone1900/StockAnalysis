import { createHash, randomUUID } from 'node:crypto';
import { readFile } from 'node:fs/promises';
import { Pool } from 'pg';
import { afterAll, beforeAll, describe, expect, it } from 'vitest';
import { ExecutionService } from '../../src/application/execution-service.js';

const url = process.env.TRADE_EXECUTION_DATABASE_URL;
const suite = url ? describe : describe.skip;
suite('执行事务、并发和重启（独立测试Schema）', () => {
  const schema = `execution_test_${randomUUID().replaceAll('-', '')}`;
  const pool = new Pool({ connectionString: url, options: `-c search_path=${schema}`, max: 4 });
  const service = () => new ExecutionService(undefined, undefined, undefined, undefined, { assertAuthorized: async () => {} }, pool);
  const command = (id: string, duplicateLeg = false) => {
    const leg = { legId: 'l', securityId: 's', side: 'BUY' as const, quantity: '10' };
    const base = { rebalanceBatchId: id, decisionId: 'd', proposalVersion: 1, approvalId: 'a', riskEvaluationId: 'r', budgetReservationId: 'b', resourceReservationId: 'resource', targetPortfolioVersion: 1, validUntil: '2099-01-01T00:00:00Z', legs: duplicateLeg ? [leg, leg] : [leg] };
    return { ...base, contentHash: createHash('sha256').update(JSON.stringify(base)).digest('hex'), idempotencyKey: id };
  };
  beforeAll(async () => {
    await pool.query(`CREATE SCHEMA ${schema}`);
    await pool.query(await readFile(new URL('../../migrations/001_execution.sql', import.meta.url), 'utf8'));
  });
  afterAll(async () => {
    await pool.query(`DROP SCHEMA ${schema} CASCADE`);
    await pool.end();
  });
  it('第二条Intent失败时批次、第一条Intent、Outbox全部回滚', async () => {
    await expect(service().createBatch(command('rollback-leg', true))).rejects.toThrow();
    for (const table of ['rebalance_batches', 'order_intents', 'execution_outbox_events']) {
      const result = await pool.query(`SELECT count(*)::int AS n FROM ${table}`);
      expect(result.rows[0].n).toBe(0);
    }
  });
  it('Outbox失败时业务写入回滚，恢复后相同幂等键可以重试', async () => {
    await pool.query("CREATE FUNCTION fail_outbox() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'injected outbox failure'; END $$");
    await pool.query('CREATE TRIGGER injected BEFORE INSERT ON execution_outbox_events FOR EACH ROW EXECUTE FUNCTION fail_outbox()');
    await expect(service().createBatch(command('rollback-outbox'))).rejects.toThrow('injected');
    expect((await pool.query('SELECT count(*)::int AS n FROM rebalance_batches')).rows[0].n).toBe(0);
    await pool.query('DROP TRIGGER injected ON execution_outbox_events');
    await expect(service().createBatch(command('rollback-outbox'))).resolves.toMatchObject({ rebalanceBatchId: 'rollback-outbox' });
  });
  it('两个独立实例并发重复请求只提交一个批次及一个事件', async () => {
    const input = command('concurrent');
    const results = await Promise.all([service().createBatch(input), service().createBatch(input)]);
    expect(results[0]).toEqual(results[1]);
    expect((await pool.query("SELECT count(*)::int AS n FROM execution_outbox_events WHERE aggregate_id = 'concurrent'")).rows[0].n).toBe(1);
    await expect(service().createBatch({ ...input, contentHash: 'x'.repeat(64) })).rejects.toThrow('conflict');
    await expect(service().createBatch({ ...input, legs: [{ ...input.legs[0]!, quantity: '999' }] })).rejects.toThrow('conflict');
  });
  it('重新实例化后恢复Intent，重复成交不重复产生Outbox', async () => {
    const batch = await service().createBatch(command('restart'));
    const intentId = batch.intents[0]!.intentId;
    await service().transitionIntent('restart', intentId, 'SUBMITTED_MANUALLY');
    const fill = { fillId: 'f', intentId, filledQuantity: '4', fillPrice: '10', occurredAt: '2026-09-05T00:00:00Z', idempotencyKey: 'fill-restart' };
    await expect(service().recordFill('restart', fill)).resolves.toMatchObject({ status: 'PARTIALLY_FILLED' });
    await expect(service().recordFill('restart', fill)).resolves.toMatchObject({ status: 'PARTIALLY_FILLED' });
    expect((await pool.query("SELECT count(*)::int AS n FROM execution_outbox_events WHERE aggregate_id = 'restart'")).rows[0].n).toBe(2);
    await expect(service().recordFill('restart', { ...fill, filledQuantity: '5' })).rejects.toThrow('conflict');
  });
});
