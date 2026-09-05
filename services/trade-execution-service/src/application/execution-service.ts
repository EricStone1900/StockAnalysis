import type { Pool } from 'pg';
import { ExecutionAggregate, executionDigest, type ApprovedExecutionCommand, type FillCommand, type OrderIntent, type OrderIntentStatus, type RebalanceBatch } from '../domain/execution.js';
import { PostgresExecutionRepository } from '../infrastructure/postgres-execution-repository.js';
import { ReconciliationAggregate, type ReconciliationCase } from '../domain/reconciliation.js';
import { ReconciliationRepository } from '../infrastructure/reconciliation-repository.js';
import { ExecutionOutboxRepository } from '../infrastructure/execution-outbox-repository.js';
import { batchCompletedEvent, batchCreatedEvent, fillRecordedEvent, reconciliationOpenedEvent } from '../domain/execution-events.js';
import { denyExecution, type ExecutionAuthorization } from './execution-authorization.js';

export class ExecutionService {
  private readonly reconciliation = new ReconciliationAggregate();
  public constructor(
    private readonly aggregate = new ExecutionAggregate(),
    private readonly repository?: PostgresExecutionRepository,
    private readonly reconciliationRepository?: ReconciliationRepository,
    private readonly outbox?: ExecutionOutboxRepository,
    private readonly authorization: ExecutionAuthorization = denyExecution,
    private readonly pool?: Pool,
  ) {}

  private async transaction<T>(work: (service: ExecutionService) => Promise<T>): Promise<T> {
    const client = await this.pool!.connect();
    try {
      await client.query('BEGIN');
      // 初期低频写入串行化，包含首次幂等查询；不同进程使用同一数据库锁。
      await client.query("SELECT pg_advisory_xact_lock(hashtext('trade-execution-write-v1'))");
      const scoped = new ExecutionService(new ExecutionAggregate(), new PostgresExecutionRepository(client), new ReconciliationRepository(client), new ExecutionOutboxRepository(client), this.authorization);
      const result = await work(scoped);
      await client.query('COMMIT');
      return result;
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally { client.release(); }
  }

  public async createBatch(command: ApprovedExecutionCommand): Promise<RebalanceBatch> {
    if (this.pool) return this.transaction((service) => service.createBatch(command));
    const repeated = await this.repository?.findByIdempotency(command.idempotencyKey);
    if (repeated) {
      if (repeated.contentHash !== command.contentHash || repeated.contentHash !== executionDigest(command)) throw new Error('idempotency payload conflict');
      return repeated;
    }
    await this.authorization.assertAuthorized(command);
    const batch = this.aggregate.createApprovedBatch(command);
    await this.repository?.append(batch, command.idempotencyKey);
    await this.outbox?.append(batchCreatedEvent(batch, command.idempotencyKey, new Date().toISOString()), batch.rebalanceBatchId);
    return batch;
  }
  public async getBatch(batchId: string): Promise<RebalanceBatch | undefined> {
    if (this.pool) {
      const batch = (await this.pool.query<{ payload: RebalanceBatch }>('SELECT payload FROM rebalance_batches WHERE rebalance_batch_id = $1', [batchId])).rows[0]?.payload;
      if (!batch) return undefined;
      const intents = await this.pool.query<{ payload: OrderIntent }>('SELECT payload FROM order_intents WHERE rebalance_batch_id = $1 ORDER BY leg_id', [batchId]);
      return { ...batch, intents: intents.rows.map((row) => row.payload) };
    }
    return this.aggregate.getBatch(batchId);
  }

  private async restore(batchId: string): Promise<void> {
    if (!this.repository) return;
    const state = await this.repository.load(batchId);
    if (!state) throw new Error('rebalance batch not found');
    this.aggregate.restore(state.batch, state.fills);
  }

  public async transitionIntent(batchId: string, intentId: string, status: OrderIntentStatus): Promise<OrderIntent> {
    if (this.pool) return this.transaction((service) => service.transitionIntent(batchId, intentId, status));
    await this.restore(batchId);
    const intent = this.aggregate.transitionIntent(batchId, intentId, status);
    await this.repository?.updateIntent(intent);
    return intent;
  }

  public async recordFill(batchId: string, fill: FillCommand): Promise<OrderIntent> {
    if (this.pool) return this.transaction((service) => service.recordFill(batchId, fill));
    await this.restore(batchId);
    const repeated = await this.repository?.findFill(fill.idempotencyKey);
    if (repeated && (repeated.fillId !== fill.fillId || repeated.intentId !== fill.intentId || repeated.filledQuantity !== fill.filledQuantity || repeated.fillPrice !== fill.fillPrice || repeated.occurredAt !== fill.occurredAt)) throw new Error('idempotency payload conflict');
    const intent = this.aggregate.recordFill(batchId, fill);
    if (repeated) return intent;
    await this.repository?.appendFill(fill);
    await this.repository?.updateIntent(intent);
    const batch = this.aggregate.getBatch(batchId);
    await this.outbox?.append(fillRecordedEvent(fill, batch, fill.idempotencyKey), batchId);
    if (batch?.intents.length && batch.intents.every((intent) => intent.status === 'FILLED')) await this.outbox?.append(batchCompletedEvent(batch, fill.idempotencyKey, fill.occurredAt), batchId);
    return intent;
  }

  public async openReconciliation(input: Parameters<ReconciliationAggregate['open']>[0]): Promise<ReconciliationCase> {
    if (this.pool) return this.transaction((service) => service.openReconciliation(input));
    const item = this.reconciliation.open(input);
    await this.reconciliationRepository?.append(item, input.idempotencyKey);
    await this.outbox?.append(reconciliationOpenedEvent(item, input.idempotencyKey), item.rebalanceBatchId);
    return item;
  }

  public async resolveReconciliation(caseId: string, status: 'RESOLVED' | 'IGNORED', reason: string, updatedAt: string): Promise<ReconciliationCase> {
    if (this.pool) return this.transaction((service) => service.resolveReconciliation(caseId, status, reason, updatedAt));
    const existing = await this.reconciliationRepository?.find(caseId);
    if (existing) this.reconciliation.restore(existing);
    const item = this.reconciliation.resolve(caseId, status, reason, updatedAt);
    await this.reconciliationRepository?.update(item);
    return item;
  }
}
