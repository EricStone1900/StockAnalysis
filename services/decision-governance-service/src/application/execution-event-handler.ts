import type { GovernanceService } from './governance-service.js';

export interface ExecutionBatchCreatedEvent {
  readonly eventId: string;
  readonly subject: string;
  readonly payload: { readonly budgetReservationId?: string };
}

/** 执行批次事件消费者；成功后才记录 eventId，失败会由消息系统重试。 */
export class ExecutionBatchEventHandler {
  private readonly handled = new Set<string>();
  public constructor(private readonly service: Pick<GovernanceService, 'consumeBudget'>) {}

  public async handle(event: ExecutionBatchCreatedEvent): Promise<boolean> {
    if (event.subject !== 'stock.trade-execution.rebalance-batch.created.v1') throw new Error('unsupported execution event subject');
    if (!event.eventId || !event.payload.budgetReservationId) throw new Error('execution event budget reference is missing');
    if (this.handled.has(event.eventId)) return false;
    await this.service.consumeBudget(event.payload.budgetReservationId);
    this.handled.add(event.eventId);
    return true;
  }
}
