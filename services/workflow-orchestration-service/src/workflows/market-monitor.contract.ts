import type { ActivityRequest, ActivityResponse, ArtifactRef } from '../activities/activity-contract.js';

export interface MarketMonitorPayload { windowStart: string; windowEnd: string; decisionAsOf: string; }
export type MarketMonitorRequest = ActivityRequest<MarketMonitorPayload>;
export interface MarketMonitorStepResult { artifactRef: ArtifactRef; severity?: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'; marketOpen?: boolean; }
export interface MarketMonitorActivities {
  checkMarketOpen(request: MarketMonitorRequest): Promise<ActivityResponse<MarketMonitorStepResult>>;
  loadAnomalySnapshot(request: MarketMonitorRequest): Promise<ActivityResponse<MarketMonitorStepResult>>;
  assessAnomaly(request: MarketMonitorRequest): Promise<ActivityResponse<MarketMonitorStepResult>>;
  publishMonitorAssessment(request: MarketMonitorRequest): Promise<ActivityResponse<MarketMonitorStepResult>>;
}
export interface MarketMonitorWorkflowResult { status: 'SKIPPED' | 'ASSESSED'; artifactRefs: readonly ArtifactRef[]; reason?: string; }

export function buildMarketMonitorRequests(request: MarketMonitorRequest): readonly MarketMonitorRequest[] {
  const base = `${request.idempotencyKey}:market-monitor`;
  return [
    { ...request, idempotencyKey: `${base}:open-check` },
    { ...request, idempotencyKey: `${base}:anomaly-snapshot` },
    { ...request, idempotencyKey: `${base}:agent-assessment` },
    { ...request, idempotencyKey: `${base}:publish-assessment` },
  ];
}

export function validateMarketMonitorResult(results: readonly ActivityResponse<MarketMonitorStepResult>[], severity: MarketMonitorStepResult['severity']): MarketMonitorWorkflowResult {
  const firstTwo = results.slice(0, 2);
  if (firstTwo.length !== 2 || firstTwo.some((result) => !result.result.artifactRef)) throw new Error('market monitor requires pre-check and anomaly artifacts');
  if (severity === 'LOW') return { status: 'SKIPPED', reason: 'LOW_SEVERITY', artifactRefs: firstTwo.map((result) => result.result.artifactRef) };
  if (results.length !== 4 || results.slice(2).some((result) => !result.result.artifactRef)) throw new Error('market monitor assessment requires four artifacts');
  return { status: 'ASSESSED', artifactRefs: results.map((result) => result.result.artifactRef) };
}
