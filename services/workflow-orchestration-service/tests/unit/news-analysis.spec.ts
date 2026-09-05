import { describe, expect, it } from 'vitest';
import { FakeNewsAnalysisActivities } from '../../src/activities/fake-activities.js';
import { buildNewsActivityRequests, validateNewsWorkflowResult, type NewsWorkflowRequest } from '../../src/workflows/news-analysis.contract.js';

const request: NewsWorkflowRequest = { workflowId: 'news-workflow-1', runId: 'run-1', correlationId: 'corr-news-1', idempotencyKey: 'news-1', payload: { sourceWindow: '2026-09-05T07:00Z', decisionAsOf: '2026-09-05T08:00:00Z', symbolScope: ['SSE:600000'] } };

describe('NewsAnalysisWorkflow contract', () => {
  it('builds the deterministic collect, candidate, analyze, publish sequence', () => {
    expect(buildNewsActivityRequests(request).map((item) => item.idempotencyKey)).toEqual(['news-1:news-analysis:collect-news', 'news-1:news-analysis:build-candidate', 'news-1:news-analysis:analyze-agent', 'news-1:news-analysis:publish-event']);
  });

  it('keeps news正文 outside workflow results and replays idempotently', async () => {
    const activities = new FakeNewsAnalysisActivities();
    const requests = buildNewsActivityRequests(request);
    const results = await Promise.all([activities.collectNews(requests[0]), activities.buildCandidate(requests[1]), activities.analyzeNewsAgent(requests[2]), activities.publishFinancialNewsEvent(requests[3])]);
    expect(await activities.analyzeNewsAgent(requests[2])).toEqual(results[2]);
    const artifacts = validateNewsWorkflowResult(results);
    expect(artifacts).toHaveLength(4);
    expect(artifacts[1].uri).toContain('news-candidate');
    expect(artifacts.every((artifact) => artifact.sha256)).toBe(true);
  });

  it('blocks completion when an event publication artifact is missing', async () => {
    const activities = new FakeNewsAnalysisActivities();
    const requests = buildNewsActivityRequests(request);
    const results = await Promise.all([activities.collectNews(requests[0]), activities.buildCandidate(requests[1]), activities.analyzeNewsAgent(requests[2]), activities.publishFinancialNewsEvent(requests[3])]);
    results[3].result.artifactRef = undefined as never;
    expect(() => validateNewsWorkflowResult(results)).toThrow('four artifact references');
  });
});
