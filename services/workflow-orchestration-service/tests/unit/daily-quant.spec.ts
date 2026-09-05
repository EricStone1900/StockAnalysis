import { describe, expect, it } from 'vitest';
import { FakeDailyQuantActivities } from '../../src/activities/fake-activities.js';
import { buildDailyQuantActivityRequests, validateDailyQuantResult, type DailyQuantRequest } from '../../src/workflows/daily-quant.contract.js';

const request: DailyQuantRequest = { workflowId: 'daily-quant-1', runId: 'run-1', correlationId: 'corr-1', idempotencyKey: 'daily-quant-1', payload: { dataVersionId: 'data-v1', decisionAsOf: '2026-09-05T08:00:00Z' } };

describe('DailyQuantAnalysisWorkflow contract', () => {
  it('builds a deterministic four-step activity sequence', () => {
    const requests = buildDailyQuantActivityRequests(request);
    expect(requests.map((item) => item.idempotencyKey)).toEqual(['daily-quant-1:daily-quant:wait-data-version', 'daily-quant-1:daily-quant:daily-analysis', 'daily-quant-1:daily-quant:active-strategy', 'daily-quant-1:daily-quant:publish-snapshots']);
    expect(requests.every((item) => item.payload === request.payload)).toBe(true);
  });

  it('publishes only artifact references and remains idempotent on activity replay', async () => {
    const activities = new FakeDailyQuantActivities();
    const requests = buildDailyQuantActivityRequests(request);
    const first = await Promise.all([activities.waitForDataVersion(requests[0]), activities.runDailyAnalysis(requests[1]), activities.runActiveStrategy(requests[2]), activities.publishSnapshots(requests[3])]);
    const replay = await activities.runDailyAnalysis(requests[1]);
    expect(replay).toEqual(first[1]);
    const result = validateDailyQuantResult(first);
    expect(result.analysisArtifact.uri).toContain('artifact://daily-analysis');
    expect(result.publishedArtifact.sha256).toHaveLength(64);
  });

  it('blocks completion when an activity omits its artifact reference', async () => {
    const activities = new FakeDailyQuantActivities();
    const requests = buildDailyQuantActivityRequests(request);
    const results = await Promise.all([activities.waitForDataVersion(requests[0]), activities.runDailyAnalysis(requests[1]), activities.runActiveStrategy(requests[2]), activities.publishSnapshots(requests[3])]);
    results[2].result.artifactRef = undefined;
    expect(() => validateDailyQuantResult(results)).toThrow('artifact references');
  });
});
