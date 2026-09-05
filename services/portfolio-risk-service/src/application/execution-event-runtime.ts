import type { ExecutionEventHandler } from './execution-event-handler.js';

export interface NatsSubscription { subscribe(subject: string, callback: (message: Uint8Array) => Promise<void>): Promise<void>; }

import { AckPolicy, createInbox, type NatsConnection } from 'nats';
export class JetStreamExecutionSubscription implements NatsSubscription {
  constructor(private readonly connection: NatsConnection, private readonly durablePrefix = 'portfolio-risk-execution') {}
  async subscribe(subject: string, callback: (message: Uint8Array) => Promise<void>): Promise<void> {
    const consumer = await this.connection.jetstream().subscribe(subject, { config: { durable_name: `${this.durablePrefix}-${subject.replaceAll('.', '-')}`, deliver_subject: createInbox(), ack_policy: AckPolicy.Explicit } });
    void (async () => { for await (const message of consumer) { try { await callback(message.data); message.ack(); } catch { /* 未确认消息由JetStream重投 */ } } })();
  }
}

/** 真实 NATS consumer 的最小适配器；消息确认由调用方在处理成功后执行。 */
export class ExecutionEventRuntime {
  constructor(private readonly subscription: NatsSubscription, private readonly handler: ExecutionEventHandler) {}
  async start(): Promise<void> {
    for (const subject of ['stock.trade-execution.fill.recorded.v1', 'stock.trade-execution.rebalance-batch.completed.v1']) await this.subscription.subscribe(subject, async (message) => { await this.handler.handle(JSON.parse(new TextDecoder().decode(message)) as never); });
  }
}
