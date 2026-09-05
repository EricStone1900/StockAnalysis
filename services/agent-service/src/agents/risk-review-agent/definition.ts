import type { AgentDefinition } from '../../application/agent-kernel.js';
import { riskReviewInputSchema, type RiskReviewInput } from './input.schema.js';
import { riskReviewOutputSchema, type RiskReviewOutput } from './output.schema.js';

const severityRank: Record<RiskReviewOutput['verdict'], number> = { PASS: 0, PASS_WITH_CONDITIONS: 1, INSUFFICIENT_EVIDENCE: 2, REJECT: 3 };

export const riskReviewDefinition: AgentDefinition<RiskReviewInput, RiskReviewOutput> = {
  id: 'risk-review', version: 'v1', promptVersion: 'risk-review-v1', maxToolCalls: 0, outputSchema: riskReviewOutputSchema,
  async invoke(untrustedInput) {
    const input = riskReviewInputSchema.parse(untrustedInput);
    const packet = input.packet;
    const hardViolation = input.riskMetrics.turnover > input.riskMetrics.maxTurnover || input.riskMetrics.estimatedCost > input.riskMetrics.maxCost || input.riskMetrics.estimatedSlippage > input.riskMetrics.maxSlippage;
    const missingLegEvidence = packet.legs.some((leg) => leg.evidenceIds.length === 0);
    let verdict: RiskReviewOutput['verdict'] = !input.providerAvailable || missingLegEvidence ? 'INSUFFICIENT_EVIDENCE' : hardViolation ? 'REJECT' : 'PASS';
    if (input.noTradeBaseline === 'SUPPORTS_HOLD' && packet.proposalAction === 'REBALANCE') verdict = 'PASS_WITH_CONDITIONS';
    if (input.secondReviewerVerdict && severityRank[input.secondReviewerVerdict] > severityRank[verdict]) verdict = input.secondReviewerVerdict;
    const riskLevel: RiskReviewOutput['riskLevel'] = verdict === 'REJECT' ? 'CRITICAL' : verdict === 'INSUFFICIENT_EVIDENCE' ? 'HIGH' : verdict === 'PASS_WITH_CONDITIONS' ? 'MEDIUM' : 'LOW';
    return {
      output: {
        decisionId: packet.decisionId, proposalVersion: packet.proposalVersion, evidencePacketHash: packet.contentHash, verdict, riskLevel,
        counterThesis: [
          ...(hardViolation ? ['成本、滑点或换手超过确定性上限。'] : []),
          ...(input.noTradeBaseline === 'SUPPORTS_HOLD' && packet.proposalAction === 'REBALANCE' ? ['NO_TRADE 基线与再平衡建议存在冲突。'] : []),
          ...(verdict === 'INSUFFICIENT_EVIDENCE' ? ['证据包不完整或复核 Provider 不可用，不能将失败解释为通过。'] : []),
        ],
        evidenceIds: packet.evidenceIds,
        validUntil: packet.validUntil,
      },
      toolCalls: [],
    };
  },
};
