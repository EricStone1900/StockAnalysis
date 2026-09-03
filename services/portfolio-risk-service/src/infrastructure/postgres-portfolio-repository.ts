import type { LedgerEntry, OpeningSnapshotCommand, PortfolioSnapshot, ReversalCommand } from '../domain/portfolio.js';

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
}
