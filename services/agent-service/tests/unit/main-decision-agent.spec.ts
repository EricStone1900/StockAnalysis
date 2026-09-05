import { describe, expect, it } from 'vitest';
import { AgentRunner } from '../../src/application/agent-kernel.js';
import { mainDecisionDefinition } from '../../src/agents/main-decision-agent/definition.js';
import type { MainDecisionInput } from '../../src/agents/main-decision-agent/input.schema.js';

const base: MainDecisionInput = {
  decisionAsOf: '2026-09-05T08:00:00Z', expiresAt: '2026-09-05T16:00:00Z', trigger: 'DAILY_TARGET', quantSnapshotId: 'quant-1',
  strategySnapshotIds: ['strategy-1'], strategies: [{ snapshotId: 'strategy-1', status: 'ACTIVE', productionVerified: true, validUntil: '2026-09-05T16:00:00Z', evidenceIds: ['evidence://strategy'] }],
  newsEventIds: ['news-event-1'], anomalyEventIds: [], marketRegimeSnapshotId: 'regime-1', portfolioSnapshotId: 'portfolio-1', portfolioEvidenceIds: ['evidence://portfolio'],
  specialistAssessments: [{ assessmentId: 'stock-assessment-1', stance: 'SUPPORT', validUntil: '2026-09-05T16:00:00Z', evidenceIds: ['evidence://stock'] }],
  contextHash: 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa', strategyDecision: 'REBALANCE_CANDIDATE', targetPortfolioVersion: 'target-1',
  targetLegs: [{ legId: 'leg-1', symbol: 'SSE:600000', side: 'BUY', targetWeight: 0.1, evidenceIds: ['evidence://target'] }], evidenceIds: ['evidence://bundle'],
};

describe('main-decision-agent', () => {
  it('creates one auditable portfolio-level rebalance with complete legs', async () => {
    const run = await new AgentRunner().run(mainDecisionDefinition, base, { correlationId: 'decision-1', inputArtifacts: [] });
    expect(run.output.proposalAction).toBe('REBALANCE');
    expect(run.output.legs).toEqual(base.targetLegs);
    expect(run.output.strategySnapshotIds).toEqual(['strategy-1']);
    expect(run.output.evidenceIds).toEqual(expect.arrayContaining(['evidence://bundle', 'evidence://target', 'evidence://stock']));
  });

  it('keeps NO_REBALANCE as a portfolio HOLD with no legs', async () => {
    const hold: MainDecisionInput = { ...base, strategyDecision: 'NO_REBALANCE', targetLegs: [] };
    const run = await new AgentRunner().run(mainDecisionDefinition, hold, { correlationId: 'decision-2', inputArtifacts: [] });
    expect(run.output.proposalAction).toBe('HOLD');
    expect(run.output.legs).toEqual([]);
    expect(run.output.rebalanceReason).toBeUndefined();
  });

  it('blocks rebalance when a specialist raises risk', async () => {
    const risk: MainDecisionInput = { ...base, specialistAssessments: [{ ...base.specialistAssessments[0], stance: 'RISK_ESCALATION' }] };
    const run = await new AgentRunner().run(mainDecisionDefinition, risk, { correlationId: 'decision-3', inputArtifacts: [] });
    expect(run.output.proposalAction).toBe('HOLD');
    expect(run.output.risks).toContain('存在风险升级证据，必须进入独立风险复核。');
  });

  it('rejects expired strategy evidence or incomplete rebalance legs', async () => {
    const expired = { ...base, strategies: [{ ...base.strategies[0], validUntil: '2026-09-05T07:59:00Z' }] };
    await expect(new AgentRunner().run(mainDecisionDefinition, expired, { correlationId: 'decision-4', inputArtifacts: [] })).rejects.toThrow('expired');
    const noLeg = { ...base, targetLegs: [] };
    await expect(new AgentRunner().run(mainDecisionDefinition, noLeg as unknown as MainDecisionInput, { correlationId: 'decision-5', inputArtifacts: [] })).rejects.toThrow('requires target legs');
  });
});
