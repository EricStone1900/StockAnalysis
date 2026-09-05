import { describe, expect, it } from 'vitest';
import { FakeMarketMonitorActivities } from '../../src/activities/fake-activities.js';
import { buildMarketMonitorRequests, validateMarketMonitorResult, type MarketMonitorRequest } from '../../src/workflows/market-monitor.contract.js';

const base: MarketMonitorRequest = { workflowId: 'monitor-1', runId: 'run-1', correlationId: 'corr-monitor-1', idempotencyKey: 'monitor-1', payload: { windowStart: '2026-09-05T07:00Z', windowEnd: '2026-09-05T08:00:00Z', decisionAsOf: '2026-09-05T08:00:00Z' } };

describe('MarketMonitorWorkflow contract', () => {
  it('only evaluates medium/high anomalies after deterministic pre-checks', async () => {
    const activities = new FakeMarketMonitorActivities();
    const requests = buildMarketMonitorRequests(base);
    const results = await Promise.all([activities.checkMarketOpen(requests[0]), activities.loadAnomalySnapshot(requests[1]), activities.assessAnomaly(requests[2]), activities.publishMonitorAssessment(requests[3])]);
    const result = validateMarketMonitorResult(results, 'HIGH');
    expect(result.status).toBe('ASSESSED');
    expect(result.artifactRefs).toHaveLength(4);
  });

  it('skips low severity without calling an Agent or publishing an assessment', async () => {
    const activities = new FakeMarketMonitorActivities();
    const low = { ...base, payload: { ...base.payload, windowStart: 'low-window' } };
    const requests = buildMarketMonitorRequests(low);
    const results = await Promise.all([activities.checkMarketOpen(requests[0]), activities.loadAnomalySnapshot(requests[1])]);
    const result = validateMarketMonitorResult(results, 'LOW');
    expect(result.status).toBe('SKIPPED');
    expect(result.reason).toBe('LOW_SEVERITY');
    expect(result.artifactRefs).toHaveLength(2);
  });

  it('blocks high severity completion when publication artifact is missing', async () => {
    const activities = new FakeMarketMonitorActivities();
    const requests = buildMarketMonitorRequests(base);
    const results = await Promise.all([activities.checkMarketOpen(requests[0]), activities.loadAnomalySnapshot(requests[1]), activities.assessAnomaly(requests[2]), activities.publishMonitorAssessment(requests[3])]);
    results[3].result.artifactRef = undefined as never;
    expect(() => validateMarketMonitorResult(results, 'HIGH')).toThrow('four artifacts');
  });
});
