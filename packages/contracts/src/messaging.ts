import type { DomainEventEnvelope } from './generated/domain-event-envelope.js';

export type Transaction = object;
export interface UnitOfWork { execute<T>(work: (transaction: Transaction) => Promise<T>): Promise<T>; }
export interface OutboxWriter { append(event: DomainEventEnvelope, transaction: Transaction): Promise<void>; }

export class InMemoryInbox {
  private readonly handled = new Set<string>();
  async once(eventId: string, handler: () => Promise<void>): Promise<boolean> {
    if (this.handled.has(eventId)) return false;
    await handler();
    this.handled.add(eventId);
    return true;
  }
}
