export interface RiskEvaluationCreatedPayload { portfolioId: string; portfolioSnapshotId: string; ledgerVersion: number; policyVersion: string; verdict: 'PASS' | 'REJECT'; }
export interface ApprovalDecidedPayload { proposalId: string; proposalVersion: number; decision: 'APPROVED' | 'REJECTED'; actorId: string; reason: string; }
export interface FillRecordedPayload { fillId: string; intentId: string; filledQuantity: string; fillPrice: string; }
import type { DomainEventEnvelope } from './generated/domain-event-envelope.js';

/** 阶段05跨服务事件统一使用的Envelope别名。 */
export type Stage05Event = DomainEventEnvelope;

export class FakeStage05Publisher {
  readonly events: Stage05Event[] = [];
  private readonly seen = new Set<string>();
  async publish(event: Stage05Event): Promise<void> {
    if (!event.eventId || !event.subject || !event.correlationId || !event.producer) throw new Error('invalid stage05 event envelope');
    if (event.availableAt < event.occurredAt) throw new Error('event availableAt precedes occurredAt');
    if (this.seen.has(event.eventId)) return;
    this.seen.add(event.eventId);
    this.events.push(event);
  }
}
