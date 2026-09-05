import { proxyActivities } from '@temporalio/workflow';
import type { ActivityRequest, ActivityResponse } from '../activities/activity-contract.js';
import type { HealthCheckPayload, HealthCheckResult } from '../activities/fake-activities.js';
import { ACTIVITY_RETRY_POLICY } from '../workflow-contract.js';

export interface HealthActivities { verifyDependency(request: ActivityRequest<HealthCheckPayload>): Promise<ActivityResponse<HealthCheckResult>>; }
const activities = proxyActivities<HealthActivities>({ startToCloseTimeout: '10 seconds', retry: ACTIVITY_RETRY_POLICY });

export async function healthWorkflow(request: ActivityRequest<HealthCheckPayload>): Promise<ActivityResponse<HealthCheckResult>> {
  return await activities.verifyDependency(request);
}
