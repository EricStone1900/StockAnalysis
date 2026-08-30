import { proxyActivities } from '@temporalio/workflow';

export interface HealthActivities { verify(): Promise<'UP'>; }
const activities = proxyActivities<HealthActivities>({ startToCloseTimeout: '10 seconds' });
export async function healthWorkflow(): Promise<'UP'> { return activities.verify(); }
