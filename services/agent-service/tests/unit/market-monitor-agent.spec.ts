import { describe, expect, it } from 'vitest';
import { AgentRunner } from '../../src/application/agent-kernel.js';
import { marketMonitorDefinition } from '../../src/agents/market-monitor-agent/definition.js';
import type { MarketMonitorAgentInput } from '../../src/agents/market-monitor-agent/input.schema.js';

const validInput: MarketMonitorAgentInput = {
  decisionAsOf: '2026-09-05T08:00:00Z',
  anomalyEvent: {
    eventId: 'anomaly-1', eventVersion: 1, symbol: 'SSE:600000',
    detectedAt: '2026-09-05T07:55:00Z', windowStart: '2026-09-05T07:50:00Z', windowEnd: '2026-09-05T07:55:00Z',
    type: 'PRICE_GAP', severity: 'HIGH',
    ruleHits: [{ ruleId: 'gap-v1', ruleVersion: '1', observedValue: -0.08, threshold: -0.05 }],
    observedFeatures: { return: -0.08, halt: null },
    marketDataVersion: 'market-data-1', watchlistVersion: 'watchlist-1', detectorVersion: 'detector-1',
    freshness: 'FRESH', evidenceIds: ['evidence://anomaly-1'],
  },
};

describe('market-monitor-agent', () => {
  it('maps anomaly severity to a bounded assessment and keeps evidence', async () => {
    const run = await new AgentRunner().run(marketMonitorDefinition, validInput, { correlationId: 'monitor-1', inputArtifacts: [] });
    expect(run.output.assessment).toBe('REASSESS');
    expect(run.output.anomalyEventId).toBe('anomaly-1');
    expect(run.output.evidenceIds).toEqual(['evidence://anomaly-1']);
    expect(run.toolCalls).toEqual([]);
  });

  it('rejects future or stale anomaly events', async () => {
    const future = { ...validInput, anomalyEvent: { ...validInput.anomalyEvent, detectedAt: '2026-09-05T09:00:00Z' } };
    await expect(new AgentRunner().run(marketMonitorDefinition, future, { correlationId: 'monitor-2', inputArtifacts: [] })).rejects.toThrow('future');
    const stale = { ...validInput, anomalyEvent: { ...validInput.anomalyEvent, freshness: 'STALE' } };
    await expect(new AgentRunner().run(marketMonitorDefinition, stale as unknown as MarketMonitorAgentInput, { correlationId: 'monitor-3', inputArtifacts: [] })).rejects.toThrow();
  });

  it('rejects raw tick fields and malformed event references', async () => {
    const rawTick = { ...validInput, tick: { price: 1 } };
    await expect(new AgentRunner().run(marketMonitorDefinition, rawTick as unknown as MarketMonitorAgentInput, { correlationId: 'monitor-4', inputArtifacts: [] })).rejects.toThrow();
    const noEvidence = { ...validInput, anomalyEvent: { ...validInput.anomalyEvent, evidenceIds: [] } };
    await expect(new AgentRunner().run(marketMonitorDefinition, noEvidence as unknown as MarketMonitorAgentInput, { correlationId: 'monitor-5', inputArtifacts: [] })).rejects.toThrow();
  });
});
