import { describe, expect, it } from 'vitest';
import { AgentRunner } from '../../src/application/agent-kernel.js';
import { strategyLearningDefinition } from '../../src/agents/strategy-learning-agent/definition.js';
import type { StrategyLearningInput } from '../../src/agents/strategy-learning-agent/input.schema.js';

const validInput: StrategyLearningInput = {
  analysisAsOf: '2026-09-05T08:00:00Z', currentStrategy: { strategyId: 'strategy-1', strategyVersion: 'v1', status: 'ACTIVE', evidenceIds: ['evidence:strategy'] }, decisionMemoryIds: ['memory-1', 'memory-2', 'memory-3'],
  outcomes: [
    { decisionId: 'decision-1', episodeType: 'FILLED', outcomeClass: 'SUCCESS', windowClosed: true, availableAt: '2026-09-03T08:00:00Z', evidenceIds: ['evidence:outcome-1'] },
    { decisionId: 'decision-2', episodeType: 'REJECTED', outcomeClass: 'COUNTEREXAMPLE', windowClosed: true, availableAt: '2026-09-03T08:00:00Z', evidenceIds: ['evidence:outcome-2'] },
    { decisionId: 'decision-3', episodeType: 'HOLD', outcomeClass: 'SUCCESS', windowClosed: true, availableAt: '2026-09-04T08:00:00Z', evidenceIds: ['evidence:outcome-3'] },
  ],
  humanFeedback: [{ feedbackId: 'feedback-1', kind: 'CORRECTED', evidenceIds: ['evidence:feedback-1'] }], minimumSamples: 3, minimumCounterexamples: 1,
};

describe('strategy-learning-agent', () => {
  it('creates a DRAFT with supporting and counterexample decisions', async () => {
    const run = await new AgentRunner().run(strategyLearningDefinition, validInput, { correlationId: 'learning-1', inputArtifacts: [] });
    expect(run.output.status).toBe('DRAFT');
    expect(run.output.supportingDecisionIds).toEqual(['decision-1', 'decision-3']);
    expect(run.output.counterexampleDecisionIds).toEqual(['decision-2']);
    expect(run.toolCalls).toEqual([]);
  });

  it('blocks one-off or no-counterexample learning claims', async () => {
    const insufficient = { ...validInput, outcomes: [validInput.outcomes[0]], minimumSamples: 3 };
    await expect(new AgentRunner().run(strategyLearningDefinition, insufficient as unknown as StrategyLearningInput, { correlationId: 'learning-2', inputArtifacts: [] })).rejects.toThrow('insufficient learning evidence');
  });

  it('rejects outcomes that were not available at analysis time', async () => {
    const future = { ...validInput, outcomes: [{ ...validInput.outcomes[0], availableAt: '2026-09-06T08:00:00Z' }, ...validInput.outcomes.slice(1)] };
    await expect(new AgentRunner().run(strategyLearningDefinition, future, { correlationId: 'learning-3', inputArtifacts: [] })).rejects.toThrow('future outcome');
  });
});
