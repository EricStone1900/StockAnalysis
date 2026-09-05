import type { FillCommand, OrderIntent, RebalanceBatch } from '../domain/execution.js';
export interface SqlClient { query<T extends Record<string, unknown> = Record<string, unknown>>(sql: string, parameters?: readonly unknown[]): Promise<{ rows: T[] }> }
export class PostgresExecutionRepository {
  public constructor(private readonly client: SqlClient) {}
  public async load(batchId: string): Promise<{ batch: RebalanceBatch; fills: FillCommand[] } | undefined> {
    const result = await this.client.query<{ payload: RebalanceBatch }>('SELECT payload FROM rebalance_batches WHERE rebalance_batch_id = $1 FOR UPDATE', [batchId]);
    const batch = result.rows[0]?.payload;
    if (!batch) return undefined;
    const intents = await this.client.query<{ payload: OrderIntent }>('SELECT payload FROM order_intents WHERE rebalance_batch_id = $1 ORDER BY leg_id', [batchId]);
    const fills = await this.client.query<{ payload: FillCommand }>('SELECT f.payload FROM execution_fills f JOIN order_intents i ON i.intent_id = f.intent_id WHERE i.rebalance_batch_id = $1', [batchId]);
    return { batch: { ...batch, intents: intents.rows.map((row) => row.payload) }, fills: fills.rows.map((row) => row.payload) };
  }
  public async findFill(key: string): Promise<FillCommand | undefined> {
    const result = await this.client.query<{ payload: FillCommand }>('SELECT payload FROM execution_fills WHERE idempotency_key = $1', [key]);
    return result.rows[0]?.payload;
  }
  public async findByIdempotency(key: string): Promise<RebalanceBatch | undefined> { const result = await this.client.query<{ payload: RebalanceBatch }>('SELECT payload FROM rebalance_batches WHERE idempotency_key = $1', [key]); return result.rows[0]?.payload; }
  public async append(batch: RebalanceBatch, idempotencyKey: string): Promise<void> { await this.client.query('INSERT INTO rebalance_batches (rebalance_batch_id, decision_id, proposal_version, approval_id, risk_evaluation_id, budget_reservation_id, resource_reservation_id, target_portfolio_version, valid_until, content_hash, payload, idempotency_key) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11::jsonb,$12)', [batch.rebalanceBatchId, batch.decisionId, batch.proposalVersion, batch.approvalId, batch.riskEvaluationId, batch.budgetReservationId, batch.resourceReservationId, batch.targetPortfolioVersion, batch.validUntil, batch.contentHash, JSON.stringify(batch), idempotencyKey]); for (const intent of batch.intents) await this.client.query('INSERT INTO order_intents (intent_id, rebalance_batch_id, leg_id, security_id, side, quantity, status, payload) VALUES ($1,$2,$3,$4,$5,$6,$7,$8::jsonb)', [intent.intentId, intent.rebalanceBatchId, intent.legId, intent.securityId, intent.side, intent.quantity, intent.status, JSON.stringify(intent)]); }
  public async updateIntent(intent: OrderIntent): Promise<void> { await this.client.query('UPDATE order_intents SET status = $1, payload = $2::jsonb WHERE intent_id = $3', [intent.status, JSON.stringify(intent), intent.intentId]); }
  public async appendFill(fill: FillCommand): Promise<void> { await this.client.query('INSERT INTO execution_fills (fill_id, intent_id, filled_quantity, fill_price, occurred_at, idempotency_key, payload) VALUES ($1,$2,$3,$4,$5,$6,$7::jsonb) ON CONFLICT (idempotency_key) DO NOTHING', [fill.fillId, fill.intentId, fill.filledQuantity, fill.fillPrice, fill.occurredAt, fill.idempotencyKey, JSON.stringify(fill)]); }
}
