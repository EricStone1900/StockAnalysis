import type { GovernanceOutboxRecord, GovernanceOutboxRepository } from '../infrastructure/governance-outbox-repository.js';

export interface GovernanceEventPublisher { publish(event: GovernanceOutboxRecord): Promise<void>; }
export class GovernanceOutboxWorker {
  public constructor(private readonly store: Pick<GovernanceOutboxRepository, 'claim' | 'markPublished'>, private readonly publisher: GovernanceEventPublisher) {}
  public async publishBatch(limit = 50): Promise<{ claimed: number; published: number; failed: number }> { const events = await this.store.claim(limit); let published = 0; for (const event of events) { try { await this.publisher.publish(event); await this.store.markPublished(event.eventId); published += 1; } catch { /* 租约到期后重试 */ } } return { claimed: events.length, published, failed: events.length - published }; }
}
