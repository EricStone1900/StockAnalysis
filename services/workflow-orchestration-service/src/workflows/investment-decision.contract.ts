import type { ActivityRequest, ActivityResponse, ArtifactRef } from '../activities/activity-contract.js';

export type InvestmentDecisionScenario = 'BLOCKED' | 'HOLD' | 'PASS' | 'RISK_REJECT' | 'HARD_REJECT';
export interface InvestmentDecisionPayload { decisionAsOf: string; trigger: 'DAILY_TARGET' | 'INTRADAY_RISK_REDUCTION' | 'EXECUTION_CORRECTION'; scenario: InvestmentDecisionScenario; }
export type InvestmentDecisionRequest = ActivityRequest<InvestmentDecisionPayload>;
export interface InvestmentDecisionStepResult { artifactRef: ArtifactRef; allowed?: boolean; proposalAction?: 'HOLD' | 'REBALANCE'; verdict?: 'PASS' | 'PASS_WITH_CONDITIONS' | 'REJECT' | 'INSUFFICIENT_EVIDENCE'; hardRiskPassed?: boolean; }
export interface InvestmentDecisionActivities {
  validateDecisionGate(request: InvestmentDecisionRequest): Promise<ActivityResponse<InvestmentDecisionStepResult>>;
  collectSpecialistEvidence(request: InvestmentDecisionRequest): Promise<ActivityResponse<InvestmentDecisionStepResult>>;
  runMainDecision(request: InvestmentDecisionRequest): Promise<ActivityResponse<InvestmentDecisionStepResult>>;
  runRiskReview(request: InvestmentDecisionRequest): Promise<ActivityResponse<InvestmentDecisionStepResult>>;
  runHardRiskEvaluation(request: InvestmentDecisionRequest): Promise<ActivityResponse<InvestmentDecisionStepResult>>;
}
export type InvestmentDecisionStatus = 'BLOCKED' | 'HOLD' | 'REJECTED' | 'READY_FOR_APPROVAL';
export interface InvestmentDecisionWorkflowResult { status: InvestmentDecisionStatus; artifactRefs: readonly ArtifactRef[]; }

export function buildInvestmentDecisionRequests(request: InvestmentDecisionRequest): readonly InvestmentDecisionRequest[] {
  const base = `${request.idempotencyKey}:investment-decision`;
  return [
    { ...request, idempotencyKey: `${base}:gate` },
    { ...request, idempotencyKey: `${base}:specialists` },
    { ...request, idempotencyKey: `${base}:main-decision` },
    { ...request, idempotencyKey: `${base}:risk-review` },
    { ...request, idempotencyKey: `${base}:hard-risk` },
  ];
}

function requireArtifact(result: ActivityResponse<InvestmentDecisionStepResult>): ArtifactRef {
  if (!result.result.artifactRef) throw new Error('investment decision activity artifact is required');
  return result.result.artifactRef;
}

export function validateInvestmentDecisionResult(status: InvestmentDecisionStatus, results: readonly ActivityResponse<InvestmentDecisionStepResult>[]): InvestmentDecisionWorkflowResult {
  const expectedCount: Record<InvestmentDecisionStatus, number> = { BLOCKED: 1, HOLD: 3, REJECTED: 4, READY_FOR_APPROVAL: 5 };
  if (results.length !== expectedCount[status]) throw new Error(`investment decision ${status} requires ${expectedCount[status]} activity artifacts`);
  const artifactRefs = results.map(requireArtifact);
  return { status, artifactRefs };
}
