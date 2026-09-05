import type { ActivityRequest, ActivityResponse, ArtifactRef } from '../activities/activity-contract.js';

export type RebalanceReason = 'DAILY_TARGET' | 'INTRADAY_RISK_REDUCTION' | 'EXECUTION_CORRECTION';
export type RebalanceExecutionScenario = 'PASS' | 'RESERVE_FAIL' | 'BATCH_FAIL' | 'UNKNOWN_ACCEPTANCE' | 'FILL_PARTIAL';
export interface RebalanceExecutionLeg { legId: string; securityId: string; side: 'BUY' | 'SELL'; quantity: string; limitPrice: string; }
export interface RebalanceExecutionFill { fillId: string; intentId: string; filledQuantity: string; fillPrice: string; occurredAt: string; idempotencyKey: string; }
export interface RebalanceExecutionPayload { portfolioId: string; decisionId: string; proposalId?: string; proposalVersion: number; tradingDate: string; batchSequence: 1 | 2; reason: RebalanceReason; scenario: RebalanceExecutionScenario; legCount: number; riskEvaluationId?: string; riskPolicyVersion?: string; feeBuffer?: string; legs?: readonly RebalanceExecutionLeg[]; approvalId?: string; budgetReservationId?: string; resourceReservationId?: string; executionContentHash?: string; targetPortfolioVersion?: number; validUntil?: string; fills?: readonly RebalanceExecutionFill[]; }
export type RebalanceExecutionRequest = ActivityRequest<RebalanceExecutionPayload>;
export interface RebalanceStepResult { artifactRef: ArtifactRef; accepted?: boolean; reservationStatus?: 'RESERVED' | 'RELEASED' | 'CONSUMED'; fillStatus?: 'COMPLETE' | 'PARTIAL' | 'UNKNOWN'; }
export interface RebalanceExecutionActivities {
  reserveBudget(request: RebalanceExecutionRequest): Promise<ActivityResponse<RebalanceStepResult>>;
  createRebalanceBatch(request: RebalanceExecutionRequest): Promise<ActivityResponse<RebalanceStepResult>>;
  createManualOrderIntents(request: RebalanceExecutionRequest): Promise<ActivityResponse<RebalanceStepResult>>;
  recordFills(request: RebalanceExecutionRequest): Promise<ActivityResponse<RebalanceStepResult>>;
  releaseBudget(request: RebalanceExecutionRequest): Promise<ActivityResponse<RebalanceStepResult>>;
}
export type RebalanceExecutionStatus = 'COMPLETED' | 'PARTIAL' | 'RELEASED' | 'UNKNOWN' | 'FAILED';
export interface RebalanceExecutionResult { status: RebalanceExecutionStatus; artifactRefs: readonly ArtifactRef[]; }

export function validateRebalanceRequest(request: RebalanceExecutionRequest): RebalanceExecutionRequest {
  const { batchSequence, reason, legCount } = request.payload;
  if (legCount < 1) throw new Error('rebalance batch requires at least one leg');
  if (batchSequence === 2 && reason === 'DAILY_TARGET') throw new Error('second batch reason is not allowed');
  return request;
}

function ref(result: ActivityResponse<RebalanceStepResult>): ArtifactRef {
  if (!result.result.artifactRef) throw new Error('rebalance activity artifact is required');
  return result.result.artifactRef;
}
export function validateRebalanceResult(status: RebalanceExecutionStatus, results: readonly ActivityResponse<RebalanceStepResult>[]): RebalanceExecutionResult {
  return { status, artifactRefs: results.map(ref) };
}
