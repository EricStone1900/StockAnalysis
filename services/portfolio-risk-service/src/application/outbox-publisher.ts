import type { OutboxEventRecord } from '../infrastructure/postgres-portfolio-repository.js';
import { Optional } from '@nestjs/common';

export interface OutboxStore {
  claimOutboxEvents(limit?: number): Promise<readonly OutboxEventRecord[]>;
  markOutboxPublished(eventId: string): Promise<void>;
}

export interface EventPublisher {
  publish(event: OutboxEventRecord): Promise<void>;
}

export interface JetStreamConnection { jetstream(): { publish(subject: string, payload: Uint8Array): Promise<unknown> } }

/** NATS JetStream 适配器不绑定具体客户端依赖，由组合根注入连接。 */
export class NatsJetStreamPublisher implements EventPublisher {
  public constructor(private readonly connection: JetStreamConnection) {}
  public async publish(event: OutboxEventRecord): Promise<void> {
    // Outbox payload 已保存完整 DomainEventEnvelope；不得在发布时丢失 schema、时间和 correlationId。
    await this.connection.jetstream().publish(event.subject, new TextEncoder().encode(JSON.stringify(event.payload)));
  }
}

export interface PublishBatchResult { readonly claimed: number; readonly published: number; readonly failed: number; }

/** 单次发布批次；失败事件不确认，由租约到期后再次领取。 */
export class OutboxPublisher {
  public constructor(private readonly store: OutboxStore, private readonly publisher: EventPublisher) {}

  public async publishBatch(limit = 50): Promise<PublishBatchResult> {
    const events = await this.store.claimOutboxEvents(limit);
    let published = 0;
    for (const event of events) {
      try {
        await this.publisher.publish(event);
        await this.store.markOutboxPublished(event.eventId);
        published += 1;
      } catch {
        // 保留未确认状态；下一轮领取会在租约到期后重试。
      }
    }
    return { claimed: events.length, published, failed: events.length - published };
  }
}

export class OutboxWorker {
  private timer: ReturnType<typeof setInterval> | undefined;
  private running = false;

  public constructor(private readonly publisher: Pick<OutboxPublisher, 'publishBatch'>, private readonly intervalMs = 5_000) {
    if (!Number.isInteger(intervalMs) || intervalMs < 100) throw new Error('invalid outbox worker interval');
  }

  public start(): void {
    if (this.running) return;
    this.running = true;
    this.timer = setInterval(() => { void this.publisher.publishBatch().catch(() => undefined); }, this.intervalMs);
    this.timer.unref?.();
  }

  public stop(): void {
    if (!this.timer) return;
    clearInterval(this.timer);
    this.timer = undefined;
    this.running = false;
  }

  public isRunning(): boolean { return this.running; }
}

export interface OutboxWorkerLifecycleHooks { start(): void; stop(): void; }

/** Nest 生命周期桥接；未配置消息发布器时保持禁用。 */
export class OutboxWorkerLifecycle {
  public constructor(@Optional() private readonly worker?: OutboxWorkerLifecycleHooks) {}
  public onApplicationBootstrap(): void { this.worker?.start(); }
  public onApplicationShutdown(): void { this.worker?.stop(); }
}
