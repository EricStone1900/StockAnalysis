import { createHash } from 'node:crypto';

export type OrderIntentStatus = 'DRAFT' | 'READY' | 'SUBMITTED_MANUALLY' | 'PARTIALLY_FILLED' | 'FILLED' | 'CANCELLED' | 'EXPIRED' | 'UNKNOWN';
export interface ApprovedExecutionCommand { readonly rebalanceBatchId: string; readonly decisionId: string; readonly proposalVersion: number; readonly approvalId: string; readonly riskEvaluationId: string; readonly budgetReservationId: string; /** 真实运行必填；保留可选以兼容历史Fixture，权威授权端口拒绝缺失值。 */ readonly resourceReservationId?: string; readonly targetPortfolioVersion: number; readonly validUntil: string; readonly legs: readonly { legId: string; securityId: string; side: 'BUY' | 'SELL'; quantity: string }[]; readonly contentHash: string; readonly idempotencyKey: string; }
export interface OrderIntent { readonly intentId: string; readonly rebalanceBatchId: string; readonly legId: string; readonly securityId: string; readonly side: 'BUY' | 'SELL'; readonly quantity: string; readonly status: OrderIntentStatus; }
export interface RebalanceBatch { readonly rebalanceBatchId: string; readonly decisionId: string; readonly proposalVersion: number; readonly approvalId: string; readonly riskEvaluationId: string; readonly budgetReservationId: string; readonly resourceReservationId?: string; readonly targetPortfolioVersion: number; readonly validUntil: string; readonly contentHash: string; readonly intents: readonly OrderIntent[]; }
export interface FillCommand { readonly fillId: string; readonly intentId: string; readonly filledQuantity: string; readonly fillPrice: string; readonly occurredAt: string; readonly idempotencyKey: string; }

export function executionDigest(command: ApprovedExecutionCommand): string {
  const canonical = { rebalanceBatchId: command.rebalanceBatchId, decisionId: command.decisionId, proposalVersion: command.proposalVersion, approvalId: command.approvalId, riskEvaluationId: command.riskEvaluationId, budgetReservationId: command.budgetReservationId, ...(command.resourceReservationId ? { resourceReservationId: command.resourceReservationId } : {}), targetPortfolioVersion: command.targetPortfolioVersion, validUntil: command.validUntil, legs: command.legs };
  return createHash('sha256').update(JSON.stringify(canonical)).digest('hex');
}

export class ExecutionAggregate {
  private readonly batches = new Map<string, RebalanceBatch>(); private readonly idempotency = new Map<string, RebalanceBatch>();
  private readonly fills = new Map<string, FillCommand>();
  restore(batch: RebalanceBatch, fills: readonly FillCommand[]): void {
    this.batches.set(batch.rebalanceBatchId, batch);
    for (const fill of fills) this.fills.set(fill.idempotencyKey, fill);
  }
  createApprovedBatch(command: ApprovedExecutionCommand): RebalanceBatch {
    const repeated = this.idempotency.get(command.idempotencyKey); if (repeated) { if (repeated.contentHash !== executionDigest(command) || repeated.contentHash !== command.contentHash) throw new Error('idempotency payload conflict'); return repeated; }
    if (this.batches.has(command.rebalanceBatchId)) throw new Error('rebalance batch already exists');
    if (!command.rebalanceBatchId || !command.decisionId || !command.approvalId || !command.riskEvaluationId || !command.budgetReservationId || command.proposalVersion < 1 || command.targetPortfolioVersion < 1) throw new Error('required execution approval field is missing');
    if (!Date.parse(command.validUntil) || new Date(command.validUntil).getTime() <= Date.now()) throw new Error('execution approval is expired');
    if (command.legs.length === 0) throw new Error('rebalance batch requires at least one leg');
    for (const leg of command.legs) { if (!leg.legId || !leg.securityId || !/^\d+(?:\.\d{1,8})?$/.test(leg.quantity) || Number(leg.quantity) <= 0) throw new Error('invalid execution leg'); }
    const canonical = { rebalanceBatchId: command.rebalanceBatchId, decisionId: command.decisionId, proposalVersion: command.proposalVersion, approvalId: command.approvalId, riskEvaluationId: command.riskEvaluationId, budgetReservationId: command.budgetReservationId, ...(command.resourceReservationId ? { resourceReservationId: command.resourceReservationId } : {}), targetPortfolioVersion: command.targetPortfolioVersion, validUntil: command.validUntil, legs: command.legs };
    if (createHash('sha256').update(JSON.stringify(canonical)).digest('hex') !== command.contentHash) throw new Error('execution content hash mismatch');
    const intents = command.legs.map((leg) => ({ intentId: `order-intent-${command.rebalanceBatchId}-${leg.legId}`, rebalanceBatchId: command.rebalanceBatchId, legId: leg.legId, securityId: leg.securityId, side: leg.side, quantity: leg.quantity, status: 'READY' as const }));
    const batch = { ...canonical, contentHash: command.contentHash, intents }; this.batches.set(command.rebalanceBatchId, batch); this.idempotency.set(command.idempotencyKey, batch); return batch;
  }
  transitionIntent(batchId: string, intentId: string, next: OrderIntentStatus): OrderIntent { const batch = this.batches.get(batchId); if (!batch) throw new Error('rebalance batch not found'); const intent = batch.intents.find((item) => item.intentId === intentId); if (!intent) throw new Error('order intent not found'); const allowed: Record<OrderIntentStatus, readonly OrderIntentStatus[]> = { DRAFT: ['READY'], READY: ['SUBMITTED_MANUALLY', 'CANCELLED', 'EXPIRED', 'UNKNOWN'], SUBMITTED_MANUALLY: ['PARTIALLY_FILLED', 'FILLED', 'CANCELLED', 'UNKNOWN'], PARTIALLY_FILLED: ['FILLED', 'CANCELLED', 'UNKNOWN'], FILLED: [], CANCELLED: [], EXPIRED: [], UNKNOWN: [] }; if (!allowed[intent.status].includes(next)) throw new Error('invalid order intent state transition'); const updated = { ...intent, status: next }; const intents = batch.intents.map((item) => item.intentId === intentId ? updated : item); this.batches.set(batchId, { ...batch, intents }); return updated; }
  recordFill(batchId: string, command: FillCommand): OrderIntent {
    const batch = this.batches.get(batchId);
    const intent = batch?.intents.find((item) => item.intentId === command.intentId);
    if (!intent) throw new Error('order intent not found');
    const repeated = this.fills.get(command.idempotencyKey);
    if (repeated) {
      if (repeated.fillId !== command.fillId || repeated.intentId !== command.intentId || repeated.filledQuantity !== command.filledQuantity || repeated.fillPrice !== command.fillPrice || repeated.occurredAt !== command.occurredAt) throw new Error('idempotency payload conflict');
      return intent;
    }
    const quantity = decimal(command.filledQuantity);
    if (!command.fillId || !command.idempotencyKey || quantity <= 0n || decimal(command.fillPrice) <= 0n || !Date.parse(command.occurredAt)) throw new Error('invalid fill');
    if ([...this.fills.values()].some((fill) => fill.fillId === command.fillId)) throw new Error('duplicate fill id');
    if (!['SUBMITTED_MANUALLY', 'PARTIALLY_FILLED'].includes(intent.status)) throw new Error('intent is not fillable');
    const total = [...this.fills.values()].filter((fill) => fill.intentId === command.intentId).reduce((sum, fill) => sum + decimal(fill.filledQuantity), quantity);
    const target = decimal(intent.quantity);
    if (total > target) throw new Error('fill exceeds order quantity');
    const updated = { ...intent, status: total === target ? 'FILLED' as const : 'PARTIALLY_FILLED' as const };
    this.batches.set(batchId, { ...batch!, intents: batch!.intents.map((item) => item.intentId === intent.intentId ? updated : item) });
    this.fills.set(command.idempotencyKey, command);
    return updated;
  }
}

function decimal(value: string): bigint {
  if (typeof value !== 'string' || !/^[0-9]+(?:[.][0-9]{1,8})?$/.test(value)) throw new Error('invalid fill decimal');
  const [whole, fraction = ''] = value.split('.');
  return BigInt(whole!) * 100_000_000n + BigInt(fraction.padEnd(8, '0'));
}
