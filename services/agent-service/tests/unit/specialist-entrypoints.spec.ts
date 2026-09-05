import { describe, expect, it } from 'vitest';
import { SpecialistEntrypoints } from '../../src/application/specialist-entrypoints.js';
import type { StockAnalysisAgentInput } from '../../src/agents/stock-analysis-agent/input.schema.js';

const input: StockAnalysisAgentInput = {
  decisionAsOf: '2026-09-05T08:00:00Z', symbol: 'SSE:600000',
  dailyAnalysisSnapshot: {
    snapshotId: 'daily-1', status: 'READY', isStale: false,
    publishedAt: '2026-09-05T07:00:00Z', validUntil: '2026-09-05T16:00:00Z',
    analyses: [{ symbol: 'SSE:600000', signal: 'BUY', evidenceIds: ['daily-1'] }], evidenceIds: ['daily-1'],
  },
  portfolio: { snapshotId: 'portfolio-1', heldSymbols: [], evidenceIds: ['portfolio-1'] },
  activeStrategySnapshots: [],
};

describe('specialist entrypoints', () => {
  it('exposes a read-only stock analysis endpoint with correlation idempotency', async () => {
    const entrypoints = new SpecialistEntrypoints();
    const command = { correlationId: 'specialist-1', input };
    const first = await entrypoints.stockAnalysis(command);
    const retry = await entrypoints.stockAnalysis({ ...command, input: { ...input, symbol: 'SSE:600001' } });
    expect(first.runId).toBe('agent-run:stock-analysis:specialist-1');
    expect(retry).toEqual(first);
    expect(first.toolCalls).toEqual([]);
  });
});
