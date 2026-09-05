import { AckPolicy, createInbox, type JetStreamManager, type JetStreamSubscription, type NatsConnection } from 'nats';
import type { RebalanceExecutionRequest } from './workflows/rebalance-execution.contract.js';
import { validateRebalanceRequest } from './workflows/rebalance-execution.contract.js';

export interface WorkflowStarterClient {
  workflow: { start(workflowType: string, options: { workflowId: string; taskQueue: string; args: [RebalanceExecutionRequest] }): Promise<unknown> };
}
interface ExecutionBatchCreatedEnvelope { eventId: string; subject: string; payload: { workflowRequest?: RebalanceExecutionRequest; workflowId?: string } }

/** 真实执行事件启动器：没有完整 Workflow 输入时拒绝启动，禁止降级到 Fake。 */
export class RebalanceExecutionEventStarter {
  private consumer?: JetStreamSubscription;
  constructor(private readonly connection: NatsConnection, private readonly manager: JetStreamManager, private readonly client: WorkflowStarterClient, private readonly taskQueue: string) {}
  async start(): Promise<void> {
    await this.manager.streams.add({ name: 'STOCK_EXECUTION', subjects: ['stock.trade-execution.>'] }).catch(() => undefined);
    this.consumer = await this.connection.jetstream().subscribe('stock.trade-execution.rebalance-batch.created.v1', { config: { durable_name: 'workflow-rebalance-execution-starter', deliver_subject: createInbox(), ack_policy: AckPolicy.Explicit } });
    void this.consume(this.consumer);
  }
  async stop(): Promise<void> { await this.consumer?.destroy(); this.consumer = undefined; }
  private async consume(consumer: JetStreamSubscription): Promise<void> {
    for await (const message of consumer) {
      try {
        const event = JSON.parse(new TextDecoder().decode(message.data)) as ExecutionBatchCreatedEnvelope;
        const request = event.payload.workflowRequest;
        if (!request) throw new Error('execution event lacks complete workflowRequest');
        validateRebalanceRequest(request);
        await this.client.workflow.start('rebalanceExecutionWorkflow', { workflowId: event.payload.workflowId ?? `rebalance-${event.eventId}`, taskQueue: this.taskQueue, args: [request] });
        message.ack();
      } catch {
        // 不确认非法或启动失败的事件，交由 JetStream 按恢复策略重投。
      }
    }
  }
}
