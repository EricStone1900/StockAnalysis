export interface ArtifactRef { uri: string; sha256: string; }

export interface ActivityRequest<TPayload> {
  workflowId: string;
  runId: string;
  correlationId: string;
  idempotencyKey: string;
  payload: TPayload;
}

export interface ActivityResponse<TPayload> {
  correlationId: string;
  result: TPayload;
  artifactRefs: readonly ArtifactRef[];
}

export function validateActivityRequest<TPayload>(request: ActivityRequest<TPayload>): ActivityRequest<TPayload> {
  if (!request.workflowId || !request.runId || !request.correlationId || !request.idempotencyKey) throw new Error('activity request requires workflow, run, correlation and idempotency identifiers');
  return request;
}
