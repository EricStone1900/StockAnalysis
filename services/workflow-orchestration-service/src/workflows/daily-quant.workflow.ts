import { proxyActivities } from '@temporalio/workflow';
import { ACTIVITY_RETRY_POLICY } from '../workflow-contract.js';
import { buildDailyQuantActivityRequests, type DailyQuantActivities, type DailyQuantRequest, validateDailyQuantResult } from './daily-quant.contract.js';

const activities = proxyActivities<DailyQuantActivities>({ startToCloseTimeout: '10 minutes', retry: ACTIVITY_RETRY_POLICY });

export async function dailyQuantAnalysisWorkflow(request: DailyQuantRequest) {
  const requests = buildDailyQuantActivityRequests(request);
  const results = [
    await activities.waitForDataVersion(requests[0]),
    await activities.runDailyAnalysis(requests[1]),
    await activities.runActiveStrategy(requests[2]),
    await activities.publishSnapshots(requests[3]),
  ];
  return validateDailyQuantResult(results);
}
