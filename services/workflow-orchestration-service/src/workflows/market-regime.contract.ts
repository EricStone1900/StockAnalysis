import type { ActivityRequest, ActivityResponse, ArtifactRef } from '../activities/activity-contract.js';

export interface MarketRegimePayload { asOf: string; universeVersion: string; regimeDefinitionVersion: string; }
export type MarketRegimeRequest = ActivityRequest<MarketRegimePayload>;
export interface MarketRegimeStepResult { artifactRef: ArtifactRef; changeDetected?: boolean; }
export interface MarketRegimeActivities {
  generateRegimeSnapshot(request: MarketRegimeRequest): Promise<ActivityResponse<MarketRegimeStepResult>>;
  analyzeMarketState(request: MarketRegimeRequest): Promise<ActivityResponse<MarketRegimeStepResult>>;
  publishRegimeAssessment(request: MarketRegimeRequest): Promise<ActivityResponse<MarketRegimeStepResult>>;
}
export interface MarketRegimeWorkflowResult { status: 'UNCHANGED' | 'CHANGED'; artifactRefs: readonly ArtifactRef[]; }

export function buildMarketRegimeRequests(request: MarketRegimeRequest): readonly MarketRegimeRequest[] {
  const base = `${request.idempotencyKey}:market-regime`;
  return [
    { ...request, idempotencyKey: `${base}:snapshot` },
    { ...request, idempotencyKey: `${base}:state-agent` },
    { ...request, idempotencyKey: `${base}:publish-assessment` },
  ];
}

export function validateMarketRegimeResult(results: readonly ActivityResponse<MarketRegimeStepResult>[], changeDetected: boolean): MarketRegimeWorkflowResult {
  if (!results[0]?.result.artifactRef) throw new Error('market regime snapshot artifact is required');
  if (!changeDetected) return { status: 'UNCHANGED', artifactRefs: [results[0].result.artifactRef] };
  if (results.length !== 3 || results.slice(1).some((result) => !result.result.artifactRef)) throw new Error('changed market regime requires assessment artifacts');
  return { status: 'CHANGED', artifactRefs: results.map((result) => result.result.artifactRef) };
}
