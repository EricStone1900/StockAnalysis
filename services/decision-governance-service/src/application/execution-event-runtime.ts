import { ExecutionBatchEventHandler, type ExecutionBatchCreatedEvent } from './execution-event-handler.js';

export interface GovernanceEventSubscription { unsubscribe(): Promise<void> | void; }
export interface GovernanceEventConnection { subscribe(subject: string, handler: (payload: Uint8Array) => Promise<void>): Promise<GovernanceEventSubscription> | GovernanceEventSubscription; }

/** NATS 订阅适配器；具体 JetStream 客户端由组合根注入。 */
export class GovernanceExecutionEventRuntime {
  private subscription: GovernanceEventSubscription | undefined;
  public constructor(private readonly connection: GovernanceEventConnection, private readonly handler: ExecutionBatchEventHandler) {}
  public async start(): Promise<void> {
    if (this.subscription) return;
    this.subscription = await this.connection.subscribe('stock.trade-execution.rebalance-batch.created.v1', async (payload) => {
      const event = JSON.parse(new TextDecoder().decode(payload)) as ExecutionBatchCreatedEvent;
      await this.handler.handle(event);
    });
  }
  public async stop(): Promise<void> {
    const subscription = this.subscription;
    this.subscription = undefined;
    await subscription?.unsubscribe();
  }
  public isRunning(): boolean { return this.subscription !== undefined; }
}
