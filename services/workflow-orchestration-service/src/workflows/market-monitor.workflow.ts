import { proxyActivities } from '@temporalio/workflow';
import { ACTIVITY_RETRY_POLICY } from '../workflow-contract.js';
import { buildMarketMonitorRequests, type MarketMonitorActivities, type MarketMonitorRequest, validateMarketMonitorResult } from './market-monitor.contract.js';

const activities = proxyActivities<MarketMonitorActivities>({ startToCloseTimeout: '5 minutes', retry: ACTIVITY_RETRY_POLICY });

export async function marketMonitorWorkflow(request: MarketMonitorRequest) {
  const requests = buildMarketMonitorRequests(request);
  const openCheck = await activities.checkMarketOpen(requests[0]);
  const anomalySnapshot = await activities.loadAnomalySnapshot(requests[1]);
  const severity = anomalySnapshot.result.severity ?? 'LOW';
  if (severity === 'LOW') return validateMarketMonitorResult([openCheck, anomalySnapshot], severity);
  const assessment = await activities.assessAnomaly(requests[2]);
  const published = await activities.publishMonitorAssessment(requests[3]);
  return validateMarketMonitorResult([openCheck, anomalySnapshot, assessment, published], severity);
}
