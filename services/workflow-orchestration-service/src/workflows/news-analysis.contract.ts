import type { ActivityRequest, ActivityResponse, ArtifactRef } from '../activities/activity-contract.js';

export interface NewsWorkflowPayload { sourceWindow: string; decisionAsOf: string; symbolScope: readonly string[]; }
export interface NewsActivityResult { artifactRef: ArtifactRef; }
export type NewsWorkflowRequest = ActivityRequest<NewsWorkflowPayload>;
export interface NewsAnalysisActivities {
  collectNews(request: NewsWorkflowRequest): Promise<ActivityResponse<NewsActivityResult>>;
  buildCandidate(request: NewsWorkflowRequest): Promise<ActivityResponse<NewsActivityResult>>;
  analyzeNewsAgent(request: NewsWorkflowRequest): Promise<ActivityResponse<NewsActivityResult>>;
  publishFinancialNewsEvent(request: NewsWorkflowRequest): Promise<ActivityResponse<NewsActivityResult>>;
}

export function buildNewsActivityRequests(request: NewsWorkflowRequest): readonly NewsWorkflowRequest[] {
  const base = `${request.idempotencyKey}:news-analysis`;
  return [
    { ...request, idempotencyKey: `${base}:collect-news` },
    { ...request, idempotencyKey: `${base}:build-candidate` },
    { ...request, idempotencyKey: `${base}:analyze-agent` },
    { ...request, idempotencyKey: `${base}:publish-event` },
  ];
}

export function validateNewsWorkflowResult(results: readonly ActivityResponse<NewsActivityResult>[]): readonly ArtifactRef[] {
  if (results.length !== 4 || results.some((result) => !result.result.artifactRef)) throw new Error('news workflow requires four artifact references');
  return results.map((result) => result.result.artifactRef);
}
