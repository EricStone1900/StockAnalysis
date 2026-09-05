import { proxyActivities } from '@temporalio/workflow';
import { ACTIVITY_RETRY_POLICY } from '../workflow-contract.js';
import { buildMarketRegimeRequests, type MarketRegimeActivities, type MarketRegimeRequest, validateMarketRegimeResult } from './market-regime.contract.js';

const activities = proxyActivities<MarketRegimeActivities>({ startToCloseTimeout: '10 minutes', retry: ACTIVITY_RETRY_POLICY });

export async function marketRegimeWorkflow(request: MarketRegimeRequest) {
  const requests = buildMarketRegimeRequests(request);
  const snapshot = await activities.generateRegimeSnapshot(requests[0]);
  const changeDetected = snapshot.result.changeDetected === true;
  if (!changeDetected) return validateMarketRegimeResult([snapshot], false);
  const assessment = await activities.analyzeMarketState(requests[1]);
  const published = await activities.publishRegimeAssessment(requests[2]);
  return validateMarketRegimeResult([snapshot, assessment, published], true);
}
