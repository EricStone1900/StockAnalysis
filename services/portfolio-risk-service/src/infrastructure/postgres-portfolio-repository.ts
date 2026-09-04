import type { CashDividendCommand, ConfirmedFillCommand, LedgerEntry, OpeningSnapshotCommand, PortfolioSnapshot, ReversalCommand, StockSplitCommand } from '../domain/portfolio.js';
import type { PortfolioValuation } from '../domain/valuation.js';
import type { RiskEvaluation } from '../domain/risk-policy.js';

export interface SqlClient {
  query<T extends Record<string, unknown> = Record<string, unknown>>(sql: string, parameters?: readonly unknown[]): Promise<{ rows: T[] }>;
}

interface TransactionClient extends SqlClient { release?: () => void }
interface PoolClient extends SqlClient { connect(): Promise<TransactionClient> }

/** PostgreSQL adapter. The concrete pg Pool is injected by the composition root. */
export class PostgresPortfolioRepository {
  constructor(private readonly client: SqlClient) {}

  async findByIdempotency(portfolioId: string, idempotencyKey: string): Promise<PortfolioSnapshot | undefined> {
    const result = await this.client.query<{ payload: PortfolioSnapshot }>(
      `SELECT payload FROM portfolio_snapshot_idempotency WHERE portfolio_id = $1 AND idempotency_key = $2`,
      [portfolioId, idempotencyKey],
    );
    return result.rows[0]?.payload;
  }

  async latest(portfolioId: string): Promise<PortfolioSnapshot | undefined> {
    const result = await this.client.query<{ payload: PortfolioSnapshot }>(
      `SELECT payload FROM portfolio_snapshots WHERE portfolio_id = $1 ORDER BY ledger_version DESC LIMIT 1`,
      [portfolioId],
    );
    return result.rows[0]?.payload;
  }

  async findEntry(entryId: string): Promise<LedgerEntry | undefined> {
    const result = await this.client.query<Record<string, unknown> & { entry_type: LedgerEntry['type']; entry_id: string; portfolio_id: string; occurred_at: string; available_at: string; source_ref: string; actor_id: string; amount: string; reason: string; correlation_id?: string }>(
      `SELECT entry_id, portfolio_id, entry_type, amount, occurred_at, available_at, source_ref, actor_id, reason, correlation_id FROM portfolio_ledger_entries WHERE entry_id = $1`, [entryId],
    );
    const row = result.rows[0];
    return row ? { entryId: row.entry_id, portfolioId: row.portfolio_id, type: row.entry_type, amount: row.amount, occurredAt: row.occurred_at, availableAt: row.available_at, sourceRef: row.source_ref, actorId: row.actor_id, reason: row.reason, correlationId: row.correlation_id as string | undefined } : undefined;
  }
  async findReversalByIdempotency(portfolioId: string, key: string): Promise<LedgerEntry | undefined> {
    const result = await this.client.query<Record<string, unknown> & { entry_id: string; portfolio_id: string; entry_type: LedgerEntry['type']; amount: string; occurred_at: string; available_at: string; source_ref: string; actor_id: string; reason: string }>(`SELECT entry_id, portfolio_id, entry_type, amount, occurred_at, available_at, source_ref, actor_id, reason FROM portfolio_ledger_entries WHERE portfolio_id = $1 AND idempotency_key = $2`, [portfolioId, key]);
    const row = result.rows[0];
    return row ? { entryId: row.entry_id, portfolioId: row.portfolio_id, type: row.entry_type, amount: row.amount, occurredAt: row.occurred_at, availableAt: row.available_at, sourceRef: row.source_ref, actorId: row.actor_id, reason: row.reason } : undefined;
  }

  async appendOpening(command: OpeningSnapshotCommand, snapshot: PortfolioSnapshot): Promise<void> {
    const connection: TransactionClient = 'connect' in this.client ? await (this.client as PoolClient).connect() : this.client;
    await connection.query('BEGIN');
    try {
      await connection.query(
      `INSERT INTO portfolio_ledger_entries
        (entry_id, portfolio_id, entry_type, amount, occurred_at, available_at, source_ref, actor_id, reason, correlation_id)
       VALUES ($1, $2, 'OPENING', $3, $4, $5, $6, $7, $8, $9)`,
      [`ledger-entry-${snapshot.snapshotId}`, command.portfolioId, command.cash, command.occurredAt, command.availableAt, command.sourceRef, command.actorId, command.reason, command.correlationId],
      );
      await connection.query(
      `INSERT INTO portfolio_snapshots
        (snapshot_id, portfolio_id, account_id, as_of, cash, positions, ledger_version, source_ref, content_hash, payload)
       VALUES ($1, $2, $3, $4, $5, $6::jsonb, $7, $8, $9, $10::jsonb)`,
      [snapshot.snapshotId, snapshot.portfolioId, snapshot.accountId, snapshot.asOf, snapshot.cash, JSON.stringify(snapshot.positions), snapshot.ledgerVersion, snapshot.sourceRef, snapshot.contentHash, JSON.stringify(snapshot)],
      );
      await connection.query(
      `INSERT INTO portfolio_snapshot_idempotency (portfolio_id, idempotency_key, snapshot_id, payload)
       VALUES ($1, $2, $3, $4::jsonb)`,
      [command.portfolioId, command.idempotencyKey, snapshot.snapshotId, JSON.stringify(snapshot)],
      );
      await connection.query('COMMIT');
    } catch (error) {
      await connection.query('ROLLBACK');
      throw error;
    } finally {
      connection.release?.();
    }
  }

  async appendReversal(command: ReversalCommand, entry: LedgerEntry): Promise<void> {
    await this.client.query(
      `INSERT INTO portfolio_ledger_entries
        (entry_id, portfolio_id, entry_type, amount, occurred_at, available_at, source_ref, actor_id, reason, reversal_of_entry_id, idempotency_key, correlation_id)
       VALUES ($1, $2, 'REVERSAL', $3, $4, $5, $6, $7, $8, $9, $10, $11)`,
      [entry.entryId, entry.portfolioId, entry.amount, entry.occurredAt, entry.availableAt, entry.sourceRef, entry.actorId, entry.reason, command.originalEntryId, command.idempotencyKey, command.correlationId],
    );
  }

  async appendConfirmedFill(command: ConfirmedFillCommand, snapshot: PortfolioSnapshot): Promise<void> {
    const connection: TransactionClient = 'connect' in this.client ? await (this.client as PoolClient).connect() : this.client;
    const entryId = `ledger-entry-${command.portfolioId}-${snapshot.ledgerVersion}`;
    await connection.query('BEGIN');
    try {
      await connection.query(
        `INSERT INTO portfolio_ledger_entries (entry_id, portfolio_id, entry_type, security_id, quantity, amount, occurred_at, available_at, source_ref, actor_id, reason, idempotency_key, correlation_id)
         VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)`,
        [entryId, command.portfolioId, command.side, command.securityId, command.quantity, multiplyDecimalForRepository(command.quantity, command.price), command.occurredAt, command.availableAt, command.sourceRef, command.actorId, command.reason, command.idempotencyKey, command.correlationId],
      );
      if (command.fee !== '0') await connection.query(
        `INSERT INTO portfolio_ledger_entries (entry_id, portfolio_id, entry_type, amount, occurred_at, available_at, source_ref, actor_id, reason, correlation_id)
         VALUES ($1, $2, 'FEE', $3, $4, $5, $6, $7, $8, $9)`,
        [`fee-${entryId}`, command.portfolioId, `-${command.fee}`, command.occurredAt, command.availableAt, command.sourceRef, command.actorId, command.reason, command.correlationId],
      );
      await connection.query(
        `INSERT INTO portfolio_snapshots (snapshot_id, portfolio_id, account_id, as_of, cash, positions, ledger_version, source_ref, content_hash, payload)
         VALUES ($1, $2, $3, $4, $5, $6::jsonb, $7, $8, $9, $10::jsonb)`,
        [snapshot.snapshotId, snapshot.portfolioId, snapshot.accountId, snapshot.asOf, snapshot.cash, JSON.stringify(snapshot.positions), snapshot.ledgerVersion, snapshot.sourceRef, snapshot.contentHash, JSON.stringify(snapshot)],
      );
      await connection.query(
        `INSERT INTO portfolio_snapshot_idempotency (portfolio_id, idempotency_key, snapshot_id, payload) VALUES ($1, $2, $3, $4::jsonb)`,
        [command.portfolioId, command.idempotencyKey, snapshot.snapshotId, JSON.stringify(snapshot)],
      );
      await connection.query('COMMIT');
    } catch (error) { await connection.query('ROLLBACK'); throw error; }
    finally { connection.release?.(); }
  }

  async appendCashDividend(command: CashDividendCommand, snapshot: PortfolioSnapshot): Promise<void> {
    const connection: TransactionClient = 'connect' in this.client ? await (this.client as PoolClient).connect() : this.client;
    const position = snapshot.positions.find((item) => item.securityId === command.securityId);
    if (!position) throw new Error('cash dividend position is missing from snapshot');
    await connection.query('BEGIN');
    try {
      await connection.query(
        `INSERT INTO portfolio_ledger_entries (entry_id, portfolio_id, entry_type, security_id, quantity, amount, occurred_at, available_at, source_ref, actor_id, reason, idempotency_key, correlation_id)
         VALUES ($1, $2, 'DIVIDEND', $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)`,
        [`dividend-${command.portfolioId}-${snapshot.ledgerVersion}`, command.portfolioId, command.securityId, position.quantity, multiplyDecimalForRepository(position.quantity, command.cashPerShare), command.occurredAt, command.availableAt, command.sourceRef, command.actorId, command.reason, command.idempotencyKey, command.correlationId],
      );
      await connection.query(
        `INSERT INTO portfolio_snapshots (snapshot_id, portfolio_id, account_id, as_of, cash, positions, ledger_version, source_ref, content_hash, payload)
         VALUES ($1, $2, $3, $4, $5, $6::jsonb, $7, $8, $9, $10::jsonb)`,
        [snapshot.snapshotId, snapshot.portfolioId, snapshot.accountId, snapshot.asOf, snapshot.cash, JSON.stringify(snapshot.positions), snapshot.ledgerVersion, snapshot.sourceRef, snapshot.contentHash, JSON.stringify(snapshot)],
      );
      await connection.query(`INSERT INTO portfolio_snapshot_idempotency (portfolio_id, idempotency_key, snapshot_id, payload) VALUES ($1, $2, $3, $4::jsonb)`, [command.portfolioId, command.idempotencyKey, snapshot.snapshotId, JSON.stringify(snapshot)]);
      await connection.query('COMMIT');
    } catch (error) { await connection.query('ROLLBACK'); throw error; }
    finally { connection.release?.(); }
  }

  async appendStockSplit(command: StockSplitCommand, snapshot: PortfolioSnapshot): Promise<void> {
    const connection: TransactionClient = 'connect' in this.client ? await (this.client as PoolClient).connect() : this.client;
    const position = snapshot.positions.find((item) => item.securityId === command.securityId);
    if (!position) throw new Error('stock split position is missing from snapshot');
    await connection.query('BEGIN');
    try {
      await connection.query(
        `INSERT INTO portfolio_ledger_entries (entry_id, portfolio_id, entry_type, security_id, quantity, amount, occurred_at, available_at, source_ref, actor_id, reason, idempotency_key, correlation_id)
         VALUES ($1, $2, 'SPLIT', $3, $4, '0', $5, $6, $7, $8, $9, $10, $11)`,
        [`split-${command.portfolioId}-${snapshot.ledgerVersion}`, command.portfolioId, command.securityId, position.quantity, command.occurredAt, command.availableAt, command.sourceRef, command.actorId, command.reason, command.idempotencyKey, command.correlationId],
      );
      await connection.query(
        `INSERT INTO portfolio_snapshots (snapshot_id, portfolio_id, account_id, as_of, cash, positions, ledger_version, source_ref, content_hash, payload)
         VALUES ($1, $2, $3, $4, $5, $6::jsonb, $7, $8, $9, $10::jsonb)`,
        [snapshot.snapshotId, snapshot.portfolioId, snapshot.accountId, snapshot.asOf, snapshot.cash, JSON.stringify(snapshot.positions), snapshot.ledgerVersion, snapshot.sourceRef, snapshot.contentHash, JSON.stringify(snapshot)],
      );
      await connection.query(`INSERT INTO portfolio_snapshot_idempotency (portfolio_id, idempotency_key, snapshot_id, payload) VALUES ($1, $2, $3, $4::jsonb)`, [command.portfolioId, command.idempotencyKey, snapshot.snapshotId, JSON.stringify(snapshot)]);
      await connection.query('COMMIT');
    } catch (error) { await connection.query('ROLLBACK'); throw error; }
    finally { connection.release?.(); }
  }

  async appendValuation(valuation: PortfolioValuation): Promise<void> {
    await this.client.query(
      `INSERT INTO portfolio_valuations (valuation_id, portfolio_id, portfolio_snapshot_id, ledger_version, market_data_version, as_of, market_value, total_equity, payload, content_hash)
       VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9::jsonb, $10)
       ON CONFLICT (portfolio_snapshot_id, market_data_version, as_of) DO NOTHING`,
      [valuation.valuationId, valuation.portfolioId, valuation.portfolioSnapshotId, valuation.ledgerVersion, valuation.marketDataVersion, valuation.asOf, valuation.marketValue, valuation.totalEquity, JSON.stringify(valuation), valuation.contentHash],
    );
  }

  async appendRiskEvaluation(evaluation: RiskEvaluation, portfolioId: string): Promise<void> {
    await this.client.query(
      `INSERT INTO portfolio_risk_evaluations (evaluation_id, portfolio_id, proposal_id, policy_version, verdict, payload, content_hash)
       VALUES ($1, $2, $3, $4, $5, $6::jsonb, $7)
       ON CONFLICT (portfolio_id, proposal_id, policy_version) DO NOTHING`,
      [evaluation.evaluationId, portfolioId, evaluation.proposalId, evaluation.policyVersion, evaluation.verdict, JSON.stringify(evaluation), evaluation.evaluationId],
    );
  }
}

function multiplyDecimalForRepository(left: string, right: string): string {
  const scale = 100_000_000n;
  const parse = (value: string) => { const [whole, fraction = ''] = value.split('.'); return BigInt(whole) * scale + BigInt((fraction + '00000000').slice(0, 8)); };
  const result = (parse(left) * parse(right)) / scale; const whole = result / scale; const fraction = (result % scale).toString().padStart(8, '0').replace(/0+$/, '');
  return `${whole}${fraction ? `.${fraction}` : ''}`;
}
