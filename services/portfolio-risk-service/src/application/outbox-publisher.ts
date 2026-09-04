import type { OutboxEventRecord } from '../infrastructure/postgres-portfolio-repository.js';

export interface OutboxStore {
  claimOutboxEvents(limit?: number): Promise<readonly OutboxEventRecord[]>;
  markOutboxPublished(eventId: string): Promise<void>;
}

export interface EventPublisher {
  publish(event: OutboxEventRecord): Promise<void>;
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
