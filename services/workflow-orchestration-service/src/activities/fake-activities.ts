import { type ActivityRequest, type ActivityResponse, validateActivityRequest } from './activity-contract.js';

export interface HealthCheckPayload { dependency: string; }
export interface HealthCheckResult { status: 'UP'; dependency: string; }

export class FakeWorkflowActivities {
  private readonly completed = new Map<string, ActivityResponse<HealthCheckResult>>();

  public async verifyDependency(request: ActivityRequest<HealthCheckPayload>): Promise<ActivityResponse<HealthCheckResult>> {
    validateActivityRequest(request);
    const existing = this.completed.get(request.idempotencyKey);
    if (existing) return existing;
    const response: ActivityResponse<HealthCheckResult> = {
      correlationId: request.correlationId,
      result: { status: 'UP', dependency: request.payload.dependency },
      artifactRefs: [],
    };
    this.completed.set(request.idempotencyKey, response);
    return response;
  }
}
