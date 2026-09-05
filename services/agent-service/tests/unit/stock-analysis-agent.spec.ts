import { describe, expect, it } from 'vitest';
import { AgentRunner } from '../../src/application/agent-kernel.js';
import { stockAnalysisDefinition } from '../../src/agents/stock-analysis-agent/definition.js';
import type { StockAnalysisAgentInput } from '../../src/agents/stock-analysis-agent/input.schema.js';

const validInput: StockAnalysisAgentInput = {
  decisionAsOf: '2026-09-05T08:00:00Z',
  symbol: 'SSE:600000',
  dailyAnalysisSnapshot: {
    snapshotId: 'daily-1', status: 'READY', isStale: false,
    publishedAt: '2026-09-05T07:00:00Z', validUntil: '2026-09-05T16:00:00Z',
    analyses: [{ symbol: 'SSE:600000', signal: 'BUY', evidenceIds: ['daily-analysis:600000'] }],
    evidenceIds: ['daily-1'],
  },
  portfolio: { snapshotId: 'portfolio-1', heldSymbols: ['SSE:600000'], evidenceIds: ['portfolio-1'] },
  activeStrategySnapshots: [
    { snapshotId: 'strategy-buy', strategyId: 'value-v1', status: 'ACTIVE', productionVerified: true, publishedAt: '2026-09-05T07:30:00Z', validUntil: '2026-09-05T16:00:00Z', rebalanceDecision: 'REBALANCE_CANDIDATE', evidenceIds: ['strategy-buy'] },
    { snapshotId: 'strategy-hold', strategyId: 'quality-v1', status: 'ACTIVE', productionVerified: true, publishedAt: '2026-09-05T07:30:00Z', validUntil: '2026-09-05T16:00:00Z', rebalanceDecision: 'NO_REBALANCE', evidenceIds: ['strategy-hold'] },
  ],
};

describe('stock-analysis-agent', () => {
  it('creates an auditable assessment and explicitly reports strategy conflict', async () => {
    const run = await new AgentRunner().run(stockAnalysisDefinition, validInput, { correlationId: 'stock-1', inputArtifacts: [] });
    expect(run.output.symbol).toBe('SSE:600000');
    expect(run.output.noTradeBaseline).toBe('SUPPORTS_HOLD');
    expect(run.output.conflictingStrategySnapshotIds).toEqual(['strategy-hold']);
    expect(run.output.evidenceIds).toEqual(expect.arrayContaining(['daily-1', 'daily-analysis:600000', 'portfolio-1', 'strategy-buy']));
    expect(run.toolCalls).toEqual([]);
  });

  it('rejects a symbol outside the published analysis snapshot', async () => {
    await expect(new AgentRunner().run(stockAnalysisDefinition, { ...validInput, symbol: 'SSE:600001' }, { correlationId: 'stock-2', inputArtifacts: [] })).rejects.toThrow('symbol must exist');
  });

  it('rejects expired or non-production strategy snapshots', async () => {
    const expired = { ...validInput, activeStrategySnapshots: [{ ...validInput.activeStrategySnapshots[0], validUntil: '2026-09-05T07:59:00Z' }] };
    await expect(new AgentRunner().run(stockAnalysisDefinition, expired, { correlationId: 'stock-3', inputArtifacts: [] })).rejects.toThrow('ACTIVE strategy snapshot');
    const candidate = { ...validInput, activeStrategySnapshots: [{ ...validInput.activeStrategySnapshots[0], status: 'CANDIDATE' }] };
    await expect(new AgentRunner().run(stockAnalysisDefinition, candidate as unknown as StockAnalysisAgentInput, { correlationId: 'stock-4', inputArtifacts: [] })).rejects.toThrow();
  });
});
