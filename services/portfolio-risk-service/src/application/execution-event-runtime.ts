import type { ExecutionEventHandler } from './execution-event-handler.js';

export interface NatsSubscription { subscribe(subject: string, callback: (message: Uint8Array) => Promise<void>): Promise<void>; }

/** 真实 NATS consumer 的最小适配器；消息确认由调用方在处理成功后执行。 */
export class ExecutionEventRuntime {
  constructor(private readonly subscription: NatsSubscription, private readonly handler: ExecutionEventHandler) {}
  async start(): Promise<void> {
    for (const subject of ['stock.trade-execution.fill.recorded.v1', 'stock.trade-execution.rebalance-batch.completed.v1']) await this.subscription.subscribe(subject, async (message) => { await this.handler.handle(JSON.parse(new TextDecoder().decode(message)) as never); });
  }
}
