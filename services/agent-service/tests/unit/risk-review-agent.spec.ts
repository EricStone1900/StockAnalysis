import { describe, expect, it } from 'vitest';
import { AgentRunner } from '../../src/application/agent-kernel.js';
import { riskReviewDefinition } from '../../src/agents/risk-review-agent/definition.js';
import { calculateEvidencePacketHash, type RiskReviewInput } from '../../src/agents/risk-review-agent/input.schema.js';

const packetWithoutHash: Omit<RiskReviewInput['packet'], 'contentHash'> = {
  decisionId: 'decision-1', proposalVersion: 1, portfolioId: 'portfolio-1', proposalAction: 'REBALANCE', targetPortfolioVersion: 'target-1',
  legs: [{ legId: 'leg-1', symbol: 'SSE:600000', side: 'BUY', targetWeight: 0.1, evidenceIds: ['evidence://leg'] }], proposalEvidenceIds: ['evidence://proposal'], strategySnapshotIds: ['strategy-1'],
  portfolioSnapshotId: 'portfolio-1', marketRegimeSnapshotId: 'regime-1', evidenceIds: ['evidence://packet'], validUntil: '2026-09-05T16:00:00Z',
};
const validInput: RiskReviewInput = {
  decisionAsOf: '2026-09-05T08:00:00Z', packet: { ...packetWithoutHash, contentHash: calculateEvidencePacketHash({ ...packetWithoutHash, contentHash: '0'.repeat(64) }) },
  riskMetrics: { turnover: 0.1, estimatedCost: 0.001, estimatedSlippage: 0.001, capacityUtilization: 0.2, maxTurnover: 0.5, maxCost: 0.01, maxSlippage: 0.01 },
  noTradeBaseline: 'SUPPORTS_TRADE', providerAvailable: true,
};

describe('risk-review-agent', () => {
  it('returns an auditable PASS for a valid immutable evidence packet', async () => {
    const run = await new AgentRunner().run(riskReviewDefinition, validInput, { correlationId: 'risk-1', inputArtifacts: [] });
    expect(run.output.verdict).toBe('PASS');
    expect(run.output.evidencePacketHash).toBe(validInput.packet.contentHash);
    expect(run.output.evidenceIds).toEqual(['evidence://packet']);
  });

  it('rejects hard risk violations and preserves the complete proposal', async () => {
    const highCost: RiskReviewInput = { ...validInput, riskMetrics: { ...validInput.riskMetrics, estimatedCost: 0.2 } };
    const run = await new AgentRunner().run(riskReviewDefinition, highCost, { correlationId: 'risk-2', inputArtifacts: [] });
    expect(run.output.verdict).toBe('REJECT');
    expect(run.output.riskLevel).toBe('CRITICAL');
  });

  it('never turns missing evidence or provider failure into PASS', async () => {
    const unavailable: RiskReviewInput = { ...validInput, providerAvailable: false };
    const run = await new AgentRunner().run(riskReviewDefinition, unavailable, { correlationId: 'risk-3', inputArtifacts: [] });
    expect(run.output.verdict).toBe('INSUFFICIENT_EVIDENCE');
    const stale = { ...validInput, packet: { ...validInput.packet, validUntil: '2026-09-05T07:59:00Z' } };
    await expect(new AgentRunner().run(riskReviewDefinition, stale as unknown as RiskReviewInput, { correlationId: 'risk-4', inputArtifacts: [] })).rejects.toThrow('expired');
  });

  it('rejects an old or tampered evidence packet hash', async () => {
    const tampered = { ...validInput, packet: { ...validInput.packet, evidenceIds: ['evidence://changed'] } };
    await expect(new AgentRunner().run(riskReviewDefinition, tampered as unknown as RiskReviewInput, { correlationId: 'risk-5', inputArtifacts: [] })).rejects.toThrow('hash mismatch');
  });
});
