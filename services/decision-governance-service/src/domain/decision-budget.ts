export interface DecisionBudgetPolicy { readonly maxDailyRebalanceBatches: number; readonly allowedSecondBatchReasons: readonly string[]; }
export interface Reservation { readonly reservationId: string; readonly portfolioId: string; readonly tradingDate: string; readonly reason: string; readonly batchNumber: number; readonly proposalId: string; readonly status: 'RESERVED' | 'RELEASED'; }

export class DecisionBudgetReservation {
  private readonly reservations = new Map<string, Reservation>();
  private readonly idempotency = new Map<string, Reservation>();
  public reserve(input: { reservationId: string; portfolioId: string; tradingDate: string; reason: string; proposalId: string; kind: 'HOLD' | 'REBALANCE'; idempotencyKey: string }, policy: DecisionBudgetPolicy): Reservation {
    const repeated = this.idempotency.get(input.idempotencyKey); if (repeated) return repeated;
    if (input.kind === 'HOLD') { const released: Reservation = { reservationId: input.reservationId, portfolioId: input.portfolioId, tradingDate: input.tradingDate, reason: input.reason, batchNumber: 0, proposalId: input.proposalId, status: 'RELEASED' }; this.idempotency.set(input.idempotencyKey, released); return released; }
    if (!/^\d{4}-\d{2}-\d{2}$/.test(input.tradingDate) || !input.portfolioId || !input.proposalId || !input.reason) throw new Error('invalid decision budget input');
    if (!Number.isInteger(policy.maxDailyRebalanceBatches) || policy.maxDailyRebalanceBatches < 1) throw new Error('invalid decision budget policy');
    const active = [...this.reservations.values()].filter((item) => item.portfolioId === input.portfolioId && item.tradingDate === input.tradingDate && item.status === 'RESERVED');
    const batchNumber = active.length + 1;
    if (batchNumber > policy.maxDailyRebalanceBatches) throw new Error('daily rebalance batch limit exceeded');
    if (batchNumber === 2 && !policy.allowedSecondBatchReasons.includes(input.reason)) throw new Error('second rebalance batch reason is not allowed');
    const reservation: Reservation = { reservationId: input.reservationId, portfolioId: input.portfolioId, tradingDate: input.tradingDate, reason: input.reason, batchNumber, proposalId: input.proposalId, status: 'RESERVED' };
    this.reservations.set(input.reservationId, reservation); this.idempotency.set(input.idempotencyKey, reservation); return reservation;
  }
  public release(reservationId: string): Reservation { const current = this.reservations.get(reservationId); if (!current) throw new Error('reservation not found'); const released = { ...current, status: 'RELEASED' as const }; this.reservations.set(reservationId, released); return released; }
}
