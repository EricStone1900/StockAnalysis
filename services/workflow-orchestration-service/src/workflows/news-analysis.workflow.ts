import { proxyActivities } from '@temporalio/workflow';
import { ACTIVITY_RETRY_POLICY } from '../workflow-contract.js';
import { buildNewsActivityRequests, type NewsAnalysisActivities, type NewsWorkflowRequest, validateNewsWorkflowResult } from './news-analysis.contract.js';

const activities = proxyActivities<NewsAnalysisActivities>({ startToCloseTimeout: '10 minutes', retry: ACTIVITY_RETRY_POLICY });

export async function newsAnalysisWorkflow(request: NewsWorkflowRequest) {
  const requests = buildNewsActivityRequests(request);
  const results = [
    await activities.collectNews(requests[0]),
    await activities.buildCandidate(requests[1]),
    await activities.analyzeNewsAgent(requests[2]),
    await activities.publishFinancialNewsEvent(requests[3]),
  ];
  return { artifacts: validateNewsWorkflowResult(results) };
}
