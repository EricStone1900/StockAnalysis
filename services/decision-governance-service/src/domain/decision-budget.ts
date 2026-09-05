export interface DecisionBudgetPolicy { readonly maxDailyRebalanceBatches: number; readonly allowedSecondBatchReasons: readonly string[]; }
export type ReservationStatus = 'RESERVED' | 'DISPATCHING' | 'CONSUMED' | 'RELEASED';
export interface Reservation { readonly reservationId: string; readonly portfolioId: string; readonly tradingDate: string; readonly reason: string; readonly batchNumber: number; readonly proposalId: string; readonly status: ReservationStatus; }

export class DecisionBudgetReservation {
  private readonly reservations = new Map<string, Reservation>();
  private readonly idempotency = new Map<string, Reservation>();
  public restore(reservation: Reservation): void { this.reservations.set(reservation.reservationId, reservation); }
  public get(reservationId: string): Reservation | undefined { return this.reservations.get(reservationId); }
  public reserve(input: { reservationId: string; portfolioId: string; tradingDate: string; reason: string; proposalId: string; kind: 'HOLD' | 'REBALANCE'; idempotencyKey: string }, policy: DecisionBudgetPolicy): Reservation {
    const repeated = this.idempotency.get(input.idempotencyKey); if (repeated) return repeated;
    if (input.kind === 'HOLD') { const released: Reservation = { reservationId: input.reservationId, portfolioId: input.portfolioId, tradingDate: input.tradingDate, reason: input.reason, batchNumber: 0, proposalId: input.proposalId, status: 'RELEASED' }; this.idempotency.set(input.idempotencyKey, released); return released; }
    if (!/^\d{4}-\d{2}-\d{2}$/.test(input.tradingDate) || !input.portfolioId || !input.proposalId || !input.reason) throw new Error('invalid decision budget input');
    if (!Number.isInteger(policy.maxDailyRebalanceBatches) || policy.maxDailyRebalanceBatches < 1) throw new Error('invalid decision budget policy');
    const active = [...this.reservations.values()].filter((item) => item.portfolioId === input.portfolioId && item.tradingDate === input.tradingDate && item.status !== 'RELEASED');
    const batchNumber = active.length + 1;
    if (batchNumber > policy.maxDailyRebalanceBatches) throw new Error('daily rebalance batch limit exceeded');
    if (batchNumber === 2 && !policy.allowedSecondBatchReasons.includes(input.reason)) throw new Error('second rebalance batch reason is not allowed');
    const reservation: Reservation = { reservationId: input.reservationId, portfolioId: input.portfolioId, tradingDate: input.tradingDate, reason: input.reason, batchNumber, proposalId: input.proposalId, status: 'RESERVED' };
    this.reservations.set(input.reservationId, reservation); this.idempotency.set(input.idempotencyKey, reservation); return reservation;
  }
  public markDispatching(reservationId: string): Reservation { const current = this.reservations.get(reservationId); if (!current) throw new Error('reservation not found'); if (current.status !== 'RESERVED') throw new Error('reservation is not dispatchable'); const updated = { ...current, status: 'DISPATCHING' as const }; this.reservations.set(reservationId, updated); return updated; }
  public consume(reservationId: string): Reservation { const current = this.reservations.get(reservationId); if (!current) throw new Error('reservation not found'); if (current.status === 'CONSUMED') return current; if (current.status !== 'DISPATCHING') throw new Error('reservation is not consumable'); const updated = { ...current, status: 'CONSUMED' as const }; this.reservations.set(reservationId, updated); return updated; }
  public release(reservationId: string): Reservation { const current = this.reservations.get(reservationId); if (!current) throw new Error('reservation not found'); if (current.status === 'CONSUMED') throw new Error('consumed reservation cannot be released'); if (current.status === 'RELEASED') return current; const released = { ...current, status: 'RELEASED' as const }; this.reservations.set(reservationId, released); return released; }
}
