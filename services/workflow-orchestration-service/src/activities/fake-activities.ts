import { type ActivityRequest, type ActivityResponse, validateActivityRequest } from './activity-contract.js';
import type { DailyQuantActivityResult, DailyQuantActivities, DailyQuantRequest } from '../workflows/daily-quant.contract.js';

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

export class FakeDailyQuantActivities implements DailyQuantActivities {
  private readonly completed = new Map<string, ActivityResponse<DailyQuantActivityResult>>();

  public async waitForDataVersion(request: DailyQuantRequest): Promise<ActivityResponse<DailyQuantActivityResult>> { return await this.complete(request, undefined); }
  public async runDailyAnalysis(request: DailyQuantRequest): Promise<ActivityResponse<DailyQuantActivityResult>> { return await this.complete(request, { uri: `artifact://daily-analysis/${request.payload.dataVersionId}`, sha256: 'a'.repeat(64) }); }
  public async runActiveStrategy(request: DailyQuantRequest): Promise<ActivityResponse<DailyQuantActivityResult>> { return await this.complete(request, { uri: `artifact://daily-strategy/${request.payload.dataVersionId}`, sha256: 'b'.repeat(64) }); }
  public async publishSnapshots(request: DailyQuantRequest): Promise<ActivityResponse<DailyQuantActivityResult>> { return await this.complete(request, { uri: `artifact://published/${request.payload.dataVersionId}`, sha256: 'c'.repeat(64) }); }

  private async complete(request: DailyQuantRequest, artifactRef: DailyQuantActivityResult['artifactRef']): Promise<ActivityResponse<DailyQuantActivityResult>> {
    validateActivityRequest(request);
    const existing = this.completed.get(request.idempotencyKey);
    if (existing) return existing;
    const response = { correlationId: request.correlationId, result: { dataVersionId: request.payload.dataVersionId, artifactRef }, artifactRefs: artifactRef ? [artifactRef] : [] };
    this.completed.set(request.idempotencyKey, response);
    return response;
  }
}
