import { describe, expect, it } from 'vitest';
import { AgentRunner } from '../../src/application/agent-kernel.js';
import { marketStateDefinition } from '../../src/agents/market-state-agent/definition.js';
import type { MarketStateAgentInput } from '../../src/agents/market-state-agent/input.schema.js';

const validInput: MarketStateAgentInput = {
  decisionAsOf: '2026-09-05T08:00:00Z',
  regimeSnapshot: {
    snapshotId: 'regime-1', asOf: '2026-09-05T07:00:00Z', frequency: 'DAILY', publishedAt: '2026-09-05T07:30:00Z',
    overallRegime: 'RISK_OFF', regimeConfidence: 0.9, previousRegime: 'NEUTRAL', changeDetected: true, transitionReason: 'breadth deteriorated',
    trend: -0.5, breadth: -0.6, volatility: 0.8, liquidity: -0.2, dataVersion: 'data-1', featureVersion: 'feature-1', regimeDefinitionVersion: 'regime-v1',
    freshness: 'FRESH', evidenceIds: ['evidence://regime-1'],
  },
  portfolioExposure: { snapshotId: 'portfolio-1', grossExposure: 0.95, industries: [{ industry: 'technology', weight: 0.4 }], evidenceIds: ['evidence://portfolio-1'] },
};

describe('market-state-agent', () => {
  it('interprets regime without changing risk policy and preserves both evidence sets', async () => {
    const run = await new AgentRunner().run(marketStateDefinition, validInput, { correlationId: 'state-1', inputArtifacts: [] });
    expect(run.output.suggestedRiskBias).toBe('CONSERVATIVE');
    expect(run.output.allowNewPositions).toBe(false);
    expect(run.output.evidenceIds).toEqual(expect.arrayContaining(['evidence://regime-1', 'evidence://portfolio-1']));
    expect(run.toolCalls).toEqual([]);
  });

  it('maps stress to defensive advice and flags high exposure', async () => {
    const stress = { ...validInput, regimeSnapshot: { ...validInput.regimeSnapshot, overallRegime: 'STRESS' } };
    const run = await new AgentRunner().run(marketStateDefinition, stress, { correlationId: 'state-2', inputArtifacts: [] });
    expect(run.output.suggestedRiskBias).toBe('DEFENSIVE');
    expect(run.output.risks).toContain('高组合暴露与防御性市场状态不匹配。');
  });

  it('rejects future, stale, and raw-market inputs', async () => {
    const future = { ...validInput, regimeSnapshot: { ...validInput.regimeSnapshot, publishedAt: '2026-09-05T09:00:00Z' } };
    await expect(new AgentRunner().run(marketStateDefinition, future, { correlationId: 'state-3', inputArtifacts: [] })).rejects.toThrow('future');
    const stale = { ...validInput, regimeSnapshot: { ...validInput.regimeSnapshot, freshness: 'STALE' } };
    await expect(new AgentRunner().run(marketStateDefinition, stale as unknown as MarketStateAgentInput, { correlationId: 'state-4', inputArtifacts: [] })).rejects.toThrow();
    const raw = { ...validInput, quotes: [{ symbol: 'SSE:600000', price: 1 }] };
    await expect(new AgentRunner().run(marketStateDefinition, raw as unknown as MarketStateAgentInput, { correlationId: 'state-5', inputArtifacts: [] })).rejects.toThrow();
  });
});
