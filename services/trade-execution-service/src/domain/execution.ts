import { createHash } from 'node:crypto';

export type OrderIntentStatus = 'DRAFT' | 'READY' | 'SUBMITTED_MANUALLY' | 'PARTIALLY_FILLED' | 'FILLED' | 'CANCELLED' | 'EXPIRED' | 'UNKNOWN';
export interface ApprovedExecutionCommand { readonly rebalanceBatchId: string; readonly decisionId: string; readonly proposalVersion: number; readonly approvalId: string; readonly riskEvaluationId: string; readonly budgetReservationId: string; readonly targetPortfolioVersion: number; readonly validUntil: string; readonly legs: readonly { legId: string; securityId: string; side: 'BUY' | 'SELL'; quantity: string }[]; readonly contentHash: string; readonly idempotencyKey: string; }
export interface OrderIntent { readonly intentId: string; readonly rebalanceBatchId: string; readonly legId: string; readonly securityId: string; readonly side: 'BUY' | 'SELL'; readonly quantity: string; readonly status: OrderIntentStatus; }
export interface RebalanceBatch { readonly rebalanceBatchId: string; readonly decisionId: string; readonly proposalVersion: number; readonly approvalId: string; readonly riskEvaluationId: string; readonly budgetReservationId: string; readonly targetPortfolioVersion: number; readonly validUntil: string; readonly contentHash: string; readonly intents: readonly OrderIntent[]; }

export class ExecutionAggregate {
  private readonly batches = new Map<string, RebalanceBatch>(); private readonly idempotency = new Map<string, RebalanceBatch>();
  createApprovedBatch(command: ApprovedExecutionCommand): RebalanceBatch {
    const repeated = this.idempotency.get(command.idempotencyKey); if (repeated) return repeated;
    if (!command.rebalanceBatchId || !command.decisionId || !command.approvalId || !command.riskEvaluationId || !command.budgetReservationId || command.proposalVersion < 1 || command.targetPortfolioVersion < 1) throw new Error('required execution approval field is missing');
    if (!Date.parse(command.validUntil) || new Date(command.validUntil).getTime() <= Date.now()) throw new Error('execution approval is expired');
    if (command.legs.length === 0) throw new Error('rebalance batch requires at least one leg');
    for (const leg of command.legs) { if (!leg.legId || !leg.securityId || !/^\d+(?:\.\d{1,8})?$/.test(leg.quantity) || Number(leg.quantity) <= 0) throw new Error('invalid execution leg'); }
    const canonical = { rebalanceBatchId: command.rebalanceBatchId, decisionId: command.decisionId, proposalVersion: command.proposalVersion, approvalId: command.approvalId, riskEvaluationId: command.riskEvaluationId, budgetReservationId: command.budgetReservationId, targetPortfolioVersion: command.targetPortfolioVersion, validUntil: command.validUntil, legs: command.legs };
    if (createHash('sha256').update(JSON.stringify(canonical)).digest('hex') !== command.contentHash) throw new Error('execution content hash mismatch');
    const intents = command.legs.map((leg) => ({ intentId: `order-intent-${command.rebalanceBatchId}-${leg.legId}`, rebalanceBatchId: command.rebalanceBatchId, legId: leg.legId, securityId: leg.securityId, side: leg.side, quantity: leg.quantity, status: 'READY' as const }));
    const batch = { ...canonical, contentHash: command.contentHash, intents }; this.batches.set(command.rebalanceBatchId, batch); this.idempotency.set(command.idempotencyKey, batch); return batch;
  }
  transitionIntent(batchId: string, intentId: string, next: OrderIntentStatus): OrderIntent { const batch = this.batches.get(batchId); if (!batch) throw new Error('rebalance batch not found'); const intent = batch.intents.find((item) => item.intentId === intentId); if (!intent) throw new Error('order intent not found'); const allowed: Record<OrderIntentStatus, readonly OrderIntentStatus[]> = { DRAFT: ['READY'], READY: ['SUBMITTED_MANUALLY', 'CANCELLED', 'EXPIRED', 'UNKNOWN'], SUBMITTED_MANUALLY: ['PARTIALLY_FILLED', 'FILLED', 'CANCELLED', 'UNKNOWN'], PARTIALLY_FILLED: ['FILLED', 'CANCELLED', 'UNKNOWN'], FILLED: [], CANCELLED: [], EXPIRED: [], UNKNOWN: [] }; if (!allowed[intent.status].includes(next)) throw new Error('invalid order intent state transition'); const updated = { ...intent, status: next }; const intents = batch.intents.map((item) => item.intentId === intentId ? updated : item); this.batches.set(batchId, { ...batch, intents }); return updated; }
}
