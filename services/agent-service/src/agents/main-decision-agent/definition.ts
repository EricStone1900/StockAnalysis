import type { AgentDefinition } from '../../application/agent-kernel.js';
import { mainDecisionInputSchema, type MainDecisionInput } from './input.schema.js';
import { mainDecisionOutputSchema, type MainDecisionOutput } from './output.schema.js';

export const mainDecisionDefinition: AgentDefinition<MainDecisionInput, MainDecisionOutput> = {
  id: 'main-decision', version: 'v1', promptVersion: 'main-decision-v1', maxToolCalls: 0, outputSchema: mainDecisionOutputSchema,
  async invoke(untrustedInput) {
    const input = mainDecisionInputSchema.parse(untrustedInput);
    const riskEscalation = input.specialistAssessments.some((assessment) => assessment.stance === 'RISK_ESCALATION');
    const rebalance = input.strategyDecision !== 'NO_REBALANCE' && !riskEscalation;
    const allEvidence = [...input.evidenceIds, ...input.portfolioEvidenceIds, ...input.strategies.flatMap((ref) => ref.evidenceIds), ...input.specialistAssessments.flatMap((ref) => ref.evidenceIds), ...input.targetLegs.flatMap((leg) => leg.evidenceIds)];
    const proposal: MainDecisionOutput = {
      decisionId: `decision:${input.portfolioSnapshotId}:${input.decisionAsOf}`,
      proposalVersion: 1,
      portfolioId: input.portfolioSnapshotId,
      proposalAction: rebalance ? 'REBALANCE' : 'HOLD',
      ...(rebalance ? { rebalanceReason: input.trigger } : {}),
      targetPortfolioVersion: input.targetPortfolioVersion,
      legs: rebalance ? input.targetLegs : [],
      confidence: riskEscalation ? 0.2 : (rebalance ? 0.75 : 0.8),
      reasons: [riskEscalation ? '专业评估触发风险升级，暂不形成可执行再平衡草稿。' : (rebalance ? 'ACTIVE 策略目标要求形成组合级再平衡草稿。' : 'NO_REBALANCE 基线支持组合级 HOLD。')],
      risks: riskEscalation ? ['存在风险升级证据，必须进入独立风险复核。'] : [],
      assumptions: ['该输出仅为组合级 TradeProposalDraft，不包含审批、预算预留、RebalanceBatch 或 Order。'],
      evidenceIds: [...new Set(allEvidence)],
      strategySnapshotIds: input.strategySnapshotIds,
      validFrom: input.decisionAsOf,
      expiresAt: input.expiresAt,
    };
    return { output: proposal, toolCalls: [] };
  },
};
