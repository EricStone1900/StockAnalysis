import { readFile } from 'node:fs/promises';
import { Pool } from 'pg';
import { afterAll, beforeAll, describe, expect, it } from 'vitest';
import { PostgresPortfolioRepository } from '../../src/infrastructure/postgres-portfolio-repository.js';
import { PortfolioLedger } from '../../src/domain/portfolio.js';
import { PortfolioService } from '../../src/application/portfolio-service.js';

const databaseUrl = process.env.PORTFOLIO_DATABASE_URL;
const suite = databaseUrl ? describe : describe.skip;

suite('PostgreSQL portfolio persistence', () => {
  const pool = new Pool({ connectionString: databaseUrl, max: 2 });
  const portfolioId = `integration-${Date.now()}`;
  const command = {
    portfolioId, accountId: 'account-integration', cash: '100.00', positions: [{ securityId: 'SSE:600000', quantity: '10' }],
    occurredAt: '2026-09-03T01:00:00Z', availableAt: '2026-09-03T01:00:00Z', sourceRef: 'integration-test', actorId: 'test', reason: '集成测试', expectedVersion: 0, idempotencyKey: 'integration-key',
  } as const;
  const concurrentCommand = { ...command, portfolioId: `${portfolioId}-concurrent`, idempotencyKey: 'concurrent-key' } as const;

  beforeAll(async () => {
    await pool.query(await readFile(new URL('../../migrations/001_portfolio_ledger.sql', import.meta.url), 'utf8'));
  });
  afterAll(async () => { for (const id of [portfolioId, concurrentCommand.portfolioId, `${portfolioId}-lock`, `${portfolioId}-fill`, `${portfolioId}-dividend`, `${portfolioId}-split`, `${portfolioId}-valuation`, `${portfolioId}-risk`]) { await pool.query('DELETE FROM portfolio_outbox_events WHERE aggregate_id = $1', [id]); await pool.query('DELETE FROM portfolio_risk_evaluations WHERE portfolio_id = $1', [id]); await pool.query('DELETE FROM portfolio_valuations WHERE portfolio_id = $1', [id]); await pool.query('DELETE FROM portfolio_snapshot_idempotency WHERE portfolio_id = $1', [id]); await pool.query('DELETE FROM portfolio_snapshots WHERE portfolio_id = $1', [id]); await pool.query('DELETE FROM portfolio_ledger_entries WHERE portfolio_id = $1', [id]); } await pool.end(); });

  it('persists and reads an immutable opening snapshot idempotently', async () => {
    const snapshot = new PortfolioLedger().importOpening(command);
    const repository = new PostgresPortfolioRepository(pool);
    await repository.appendOpening(command, snapshot);
    await expect(repository.latest(portfolioId)).resolves.toEqual(snapshot);
    await expect(repository.findByIdempotency(portfolioId, command.idempotencyKey)).resolves.toEqual(snapshot);
  });

  it('rolls back all writes when a later insert fails', async () => {
    const snapshot = new PortfolioLedger().importOpening({ ...command, idempotencyKey: 'rollback-key' });
    const repository = new PostgresPortfolioRepository(pool);
    await expect(repository.appendOpening({ ...command, idempotencyKey: 'integration-key' }, snapshot)).rejects.toThrow();
    const count = await pool.query<{ count: string }>('SELECT count(*)::text AS count FROM portfolio_ledger_entries WHERE entry_id = $1', [`ledger-entry-${snapshot.snapshotId}`]);
    expect(count.rows[0]?.count).toBe('1');
  });

  it('returns one committed snapshot for concurrent identical commands', async () => {
    const first = new PortfolioService(new PortfolioLedger(), new PostgresPortfolioRepository(pool));
    const second = new PortfolioService(new PortfolioLedger(), new PostgresPortfolioRepository(pool));
    const [left, right] = await Promise.all([first.importOpening(concurrentCommand), second.importOpening(concurrentCommand)]);
    expect(left.snapshotId).toBe(right.snapshotId);
  });

  it('allows only one of two concurrent different commands at the same version', async () => {
    const base = { ...concurrentCommand, portfolioId: `${portfolioId}-lock` };
    const left = new PortfolioService(new PortfolioLedger(), new PostgresPortfolioRepository(pool));
    const right = new PortfolioService(new PortfolioLedger(), new PostgresPortfolioRepository(pool));
    const results = await Promise.allSettled([left.importOpening({ ...base, idempotencyKey: 'lock-left' }), right.importOpening({ ...base, idempotencyKey: 'lock-right' })]);
    expect(results.filter((result) => result.status === 'fulfilled')).toHaveLength(1);
    expect(results.filter((result) => result.status === 'rejected')).toHaveLength(1);
  });

  it('atomically persists a confirmed fill, fee and derived snapshot', async () => {
    const fillPortfolioId = `${portfolioId}-fill`;
    const repository = new PostgresPortfolioRepository(pool);
    const service = new PortfolioService(new PortfolioLedger(), repository);
    await service.importOpening({ ...command, portfolioId: fillPortfolioId, cash: '1000', positions: [], idempotencyKey: 'fill-opening' });
    const snapshot = await service.recordConfirmedFill({ portfolioId: fillPortfolioId, securityId: 'SSE:600000', side: 'BUY', quantity: '10', price: '12.34', fee: '0.50', occurredAt: '2026-09-03T02:00:00Z', availableAt: '2026-09-03T02:00:00Z', sourceRef: 'fill-test', actorId: 'test', reason: 'confirmed', expectedVersion: 1, idempotencyKey: 'fill-1' });
    expect(snapshot).toMatchObject({ cash: '876.1', ledgerVersion: 2 });
    await expect(repository.latest(fillPortfolioId)).resolves.toEqual(snapshot);
    const count = await pool.query<{ count: string }>('SELECT count(*)::text AS count FROM portfolio_ledger_entries WHERE portfolio_id = $1', [fillPortfolioId]);
    expect(count.rows[0]?.count).toBe('3');
  });

  it('atomically persists a cash dividend and derived snapshot', async () => {
    const dividendPortfolioId = `${portfolioId}-dividend`;
    const repository = new PostgresPortfolioRepository(pool);
    const service = new PortfolioService(new PortfolioLedger(), repository);
    await service.importOpening({ ...command, portfolioId: dividendPortfolioId, cash: '1000', positions: [{ securityId: 'SSE:600000', quantity: '100' }], idempotencyKey: 'dividend-opening' });
    const snapshot = await service.recordCashDividend({ portfolioId: dividendPortfolioId, securityId: 'SSE:600000', cashPerShare: '0.25', occurredAt: '2026-09-03T04:00:00Z', availableAt: '2026-09-03T04:00:00Z', sourceRef: 'dividend-test', actorId: 'test', reason: 'cash dividend', expectedVersion: 1, idempotencyKey: 'dividend-1' });
    expect(snapshot).toMatchObject({ cash: '1025', ledgerVersion: 2 });
    const entry = await pool.query<{ entry_type: string; amount: string }>('SELECT entry_type, amount FROM portfolio_ledger_entries WHERE portfolio_id = $1 AND entry_type = $2', [dividendPortfolioId, 'DIVIDEND']);
    expect(entry.rows[0]).toEqual({ entry_type: 'DIVIDEND', amount: '25' });
  });

  it('atomically persists a stock split and derived snapshot', async () => {
    const splitPortfolioId = `${portfolioId}-split`;
    const repository = new PostgresPortfolioRepository(pool);
    const service = new PortfolioService(new PortfolioLedger(), repository);
    await service.importOpening({ ...command, portfolioId: splitPortfolioId, cash: '1000', positions: [{ securityId: 'SSE:600000', quantity: '100' }], idempotencyKey: 'split-opening' });
    const snapshot = await service.recordStockSplit({ portfolioId: splitPortfolioId, securityId: 'SSE:600000', numerator: 2, denominator: 1, occurredAt: '2026-09-03T05:00:00Z', availableAt: '2026-09-03T05:00:00Z', sourceRef: 'split-test', actorId: 'test', reason: 'split', expectedVersion: 1, idempotencyKey: 'split-1' });
    expect(snapshot).toMatchObject({ cash: '1000', ledgerVersion: 2 }); expect(snapshot.positions[0]?.quantity).toBe('200');
    const entry = await pool.query<{ entry_type: string; quantity: string }>('SELECT entry_type, quantity FROM portfolio_ledger_entries WHERE portfolio_id = $1 AND entry_type = $2', [splitPortfolioId, 'SPLIT']);
    expect(entry.rows[0]).toEqual({ entry_type: 'SPLIT', quantity: '200' });
  });

  it('persists a valuation bound to snapshot and market data version', async () => {
    const valuationPortfolioId = `${portfolioId}-valuation`;
    const repository = new PostgresPortfolioRepository(pool);
    const service = new PortfolioService(new PortfolioLedger(), repository);
    await service.importOpening({ ...command, portfolioId: valuationPortfolioId, cash: '100', positions: [{ securityId: 'SSE:600000', quantity: '10' }], idempotencyKey: 'valuation-opening' });
    const valuation = await service.valueLatest(valuationPortfolioId, [{ securityId: 'SSE:600000', close: '12.34', asOf: '2026-09-03T01:00:00Z' }], 'market-v1', '2026-09-03T01:00:00Z', 5);
    expect(valuation.totalEquity).toBe('223.4');
    const stored = await pool.query<{ market_data_version: string; total_equity: string }>('SELECT market_data_version, total_equity FROM portfolio_valuations WHERE portfolio_id = $1', [valuationPortfolioId]);
    expect(stored.rows[0]).toEqual({ market_data_version: 'market-v1', total_equity: '223.4' });
  });

  it('atomically persists risk evaluation and its outbox event idempotently', async () => {
    const riskPortfolioId = `${portfolioId}-risk`;
    const repository = new PostgresPortfolioRepository(pool);
    const service = new PortfolioService(new PortfolioLedger(), repository);
    await service.importOpening({ ...command, portfolioId: riskPortfolioId, cash: '1000', positions: [{ securityId: 'SSE:600000', quantity: '10' }], idempotencyKey: 'risk-opening' });
    const input = { portfolioId: riskPortfolioId, proposalId: 'proposal-risk-1', reason: 'NORMAL', legs: [{ securityId: 'SSE:600000' as const, side: 'HOLD' as const, quantity: '0', price: '10' }], prices: { 'SSE:600000': '10' }, decisionBudget: { rebalanceBatchesToday: 0 }, peakEquity: '1100', policy: { policyVersion: 'policy-v1', maxPositionWeight: '0.9', maxTotalPositionWeight: '0.9', minCash: '0', maxTurnover: '500', maxDailyRebalanceBatches: 2, allowedSecondBatchReasons: [], maxDrawdown: '1000', paused: false } };
    const first = await service.evaluateRisk(input);
    const second = await service.evaluateRisk(input);
    expect(second.evaluationId).toBe(first.evaluationId);
    const evaluations = await pool.query<{ count: string }>('SELECT count(*)::text AS count FROM portfolio_risk_evaluations WHERE portfolio_id = $1', [riskPortfolioId]);
    const events = await pool.query<{ count: string }>('SELECT count(*)::text AS count FROM portfolio_outbox_events WHERE aggregate_id = $1', [riskPortfolioId]);
    expect(evaluations.rows[0]?.count).toBe('1');
    expect(events.rows[0]?.count).toBe('1');
  });
});
