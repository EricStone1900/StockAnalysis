/** 执行授权和资源占用的跨服务契约；来源为ADR-020。 */
export type ResourceReservationStatus = 'RESERVED' | 'DISPATCHING' | 'IN_FLIGHT' | 'UNKNOWN' | 'SETTLED' | 'RELEASED';
export interface ExecutionLeg { readonly legId: string; readonly securityId: string; readonly side: 'BUY' | 'SELL'; readonly quantity: string; readonly limitPrice: string; }
export interface ResourceReservationRequest {
  readonly reservationId: string;
  readonly portfolioId: string;
  readonly ledgerVersion: number;
  readonly decisionId: string;
  readonly proposalVersion: number;
  readonly riskEvaluationId: string;
  readonly riskPolicyVersion: string;
  readonly executionContentHash: string;
  readonly feeBuffer: string;
  readonly legs: readonly ExecutionLeg[];
  readonly idempotencyKey: string;
}
export interface ResourceReservation {
  readonly reservationId: string;
  readonly portfolioId: string;
  readonly ledgerVersion: number;
  readonly decisionId: string;
  readonly proposalVersion: number;
  readonly riskEvaluationId: string;
  readonly riskPolicyVersion: string;
  readonly executionContentHash: string;
  readonly reservedCash: string;
  readonly reservedSells: Readonly<Record<string, string>>;
  readonly status: ResourceReservationStatus;
}
export interface ExecutionAuthorizationGrant {
  readonly decisionId: string;
  readonly proposalVersion: number;
  readonly approvalId: string;
  readonly riskEvaluationId: string;
  readonly budgetReservationId: string;
  readonly resourceReservationId: string;
  readonly targetPortfolioVersion: number;
  readonly executionContentHash: string;
  readonly validUntil: string;
}
