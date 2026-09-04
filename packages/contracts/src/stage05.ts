export interface RiskEvaluationCreatedPayload { portfolioId: string; portfolioSnapshotId: string; ledgerVersion: number; policyVersion: string; verdict: 'PASS' | 'REJECT'; }
export interface ApprovalDecidedPayload { proposalId: string; proposalVersion: number; decision: 'APPROVED' | 'REJECTED'; actorId: string; reason: string; }
export interface FillRecordedPayload { fillId: string; intentId: string; filledQuantity: string; fillPrice: string; }
export interface Stage05Event { eventId: string; subject: string; correlationId: string; payload: Record<string, unknown>; }
export class FakeStage05Publisher {
  readonly events: Stage05Event[] = [];
  private readonly seen = new Set<string>();
  async publish(event: Stage05Event): Promise<void> { if (this.seen.has(event.eventId)) return; this.seen.add(event.eventId); this.events.push(event); }
}
