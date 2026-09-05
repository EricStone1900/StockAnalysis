import type { ActivityRequest, ActivityResponse, ArtifactRef } from '../activities/activity-contract.js';

export interface DailyQuantPayload { dataVersionId: string; decisionAsOf: string; }
export interface DailyQuantActivityResult { dataVersionId: string; artifactRef?: ArtifactRef; }
export interface DailyQuantWorkflowResult {
  dataVersionId: string;
  analysisArtifact: ArtifactRef;
  strategyArtifact: ArtifactRef;
  publishedArtifact: ArtifactRef;
}

export type DailyQuantRequest = ActivityRequest<DailyQuantPayload>;

export interface DailyQuantActivities {
  waitForDataVersion(request: DailyQuantRequest): Promise<ActivityResponse<DailyQuantActivityResult>>;
  runDailyAnalysis(request: DailyQuantRequest): Promise<ActivityResponse<DailyQuantActivityResult>>;
  runActiveStrategy(request: DailyQuantRequest): Promise<ActivityResponse<DailyQuantActivityResult>>;
  publishSnapshots(request: DailyQuantRequest): Promise<ActivityResponse<DailyQuantActivityResult>>;
}

export function buildDailyQuantActivityRequests(request: DailyQuantRequest): readonly DailyQuantRequest[] {
  const base = `${request.idempotencyKey}:daily-quant`;
  return [
    { ...request, idempotencyKey: `${base}:wait-data-version` },
    { ...request, idempotencyKey: `${base}:daily-analysis` },
    { ...request, idempotencyKey: `${base}:active-strategy` },
    { ...request, idempotencyKey: `${base}:publish-snapshots` },
  ];
}

export function validateDailyQuantResult(result: readonly ActivityResponse<DailyQuantActivityResult>[]): DailyQuantWorkflowResult {
  if (result.length !== 4 || result.some((item) => !item.result.dataVersionId)) throw new Error('daily quant workflow requires four successful activities');
  const refs = result.slice(1).map((item) => item.result.artifactRef);
  if (refs.some((ref) => !ref)) throw new Error('daily quant workflow activities must return artifact references');
  return { dataVersionId: result[0].result.dataVersionId, analysisArtifact: refs[0]!, strategyArtifact: refs[1]!, publishedArtifact: refs[2]! };
}
