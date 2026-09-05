import { describe, expect, it } from 'vitest';
import { FakeMarketRegimeActivities } from '../../src/activities/fake-activities.js';
import { buildMarketRegimeRequests, validateMarketRegimeResult, type MarketRegimeRequest } from '../../src/workflows/market-regime.contract.js';

const base: MarketRegimeRequest = { workflowId: 'regime-1', runId: 'run-1', correlationId: 'corr-regime-1', idempotencyKey: 'regime-1', payload: { asOf: '2026-09-05T08:00:00Z', universeVersion: 'universe-v1', regimeDefinitionVersion: 'regime-v1' } };

describe('MarketRegimeWorkflow contract', () => {
  it('stores an unchanged snapshot without calling the state Agent', async () => {
    const activities = new FakeMarketRegimeActivities();
    const requests = buildMarketRegimeRequests(base);
    const snapshot = await activities.generateRegimeSnapshot(requests[0]);
    const result = validateMarketRegimeResult([snapshot], false);
    expect(result.status).toBe('UNCHANGED');
    expect(result.artifactRefs).toHaveLength(1);
  });

  it('calls market-state Agent only when the regime changes', async () => {
    const activities = new FakeMarketRegimeActivities();
    const changed = { ...base, payload: { ...base.payload, universeVersion: 'universe-changed' } };
    const requests = buildMarketRegimeRequests(changed);
    const snapshot = await activities.generateRegimeSnapshot(requests[0]);
    const assessment = await activities.analyzeMarketState(requests[1]);
    const published = await activities.publishRegimeAssessment(requests[2]);
    const result = validateMarketRegimeResult([snapshot, assessment, published], true);
    expect(result.status).toBe('CHANGED');
    expect(result.artifactRefs).toHaveLength(3);
  });

  it('blocks changed-regime completion without the published assessment artifact', async () => {
    const activities = new FakeMarketRegimeActivities();
    const requests = buildMarketRegimeRequests({ ...base, payload: { ...base.payload, universeVersion: 'universe-changed' } });
    const snapshot = await activities.generateRegimeSnapshot(requests[0]);
    const assessment = await activities.analyzeMarketState(requests[1]);
    expect(() => validateMarketRegimeResult([snapshot, assessment], true)).toThrow('assessment artifacts');
  });
});
