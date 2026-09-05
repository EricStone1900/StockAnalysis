import type { ResourceReservationStatus } from '@stock/contracts';
import type { PortfolioService } from './portfolio-service.js';
import type { ResourceReservationService } from './resource-reservation-service.js';

interface Envelope { readonly eventId: string; readonly subject: string; readonly correlationId?: string; readonly occurredAt: string; readonly payload: Record<string, unknown>; }
interface FillPayload { readonly portfolioId?: string; readonly rebalanceBatchId?: string; readonly resourceReservationId?: string; readonly securityId?: string; readonly side?: 'BUY' | 'SELL'; readonly filledQuantity?: string; readonly fillPrice?: string; readonly fillId?: string; readonly intentId?: string; }
interface CompletedPayload { readonly resourceReservationId?: string; }

/** Execution事件的Inbox语义：先按eventId去重，再写账本/资源状态。 */
export class ExecutionEventHandler {
  private readonly processed = new Set<string>();
  constructor(private readonly portfolios: Pick<PortfolioService, 'latest' | 'recordConfirmedFill'>, private readonly resources: Pick<ResourceReservationService, 'transition'>, private readonly inbox?: { accept(event: { eventId: string; subject: string }): Promise<boolean>; release?(eventId: string): Promise<void> }) {}
  async handle(event: Envelope): Promise<void> {
    if (this.inbox ? !(await this.inbox.accept(event)) : this.processed.has(event.eventId)) return;
    try {
      if (event.subject === 'stock.trade-execution.fill.recorded.v1') await this.handleFill(event, event.payload as FillPayload);
      else if (event.subject === 'stock.trade-execution.rebalance-batch.completed.v1') await this.handleCompleted(event, event.payload as CompletedPayload);
      else return;
      if (!this.inbox) this.processed.add(event.eventId);
    } catch (error) {
      await this.inbox?.release?.(event.eventId);
      throw error;
    }
  }
  private async handleFill(event: Envelope, payload: FillPayload): Promise<void> {
    if (!payload.portfolioId || !payload.securityId || !payload.side || !payload.filledQuantity || !payload.fillPrice || !payload.fillId || !payload.intentId) throw new Error('execution fill event is incomplete');
    const current = await this.portfolios.latest(payload.portfolioId); if (!current) throw new Error('portfolio snapshot not found');
    await this.portfolios.recordConfirmedFill({ portfolioId: payload.portfolioId, securityId: payload.securityId, side: payload.side, quantity: payload.filledQuantity, price: payload.fillPrice, fee: '0', occurredAt: event.occurredAt, availableAt: event.occurredAt, sourceRef: payload.rebalanceBatchId ?? payload.fillId, actorId: 'trade-execution-service', reason: 'execution fill', expectedVersion: current.ledgerVersion, idempotencyKey: payload.fillId, correlationId: event.correlationId });
    if (payload.resourceReservationId) await this.safeTransition(payload.resourceReservationId, 'IN_FLIGHT');
  }
  private async handleCompleted(event: Envelope, payload: CompletedPayload): Promise<void> { if (!payload.resourceReservationId) throw new Error('execution completion resource reference is missing'); await this.resources.transition(payload.resourceReservationId, 'SETTLED'); }
  private async safeTransition(id: string, status: ResourceReservationStatus): Promise<void> { try { await this.resources.transition(id, status); } catch (error) { if (!(error instanceof Error) || !/invalid resource reservation transition/.test(error.message)) throw error; } }
}
