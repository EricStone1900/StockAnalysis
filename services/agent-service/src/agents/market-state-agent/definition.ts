import type { AgentDefinition } from '../../application/agent-kernel.js';
import { marketStateInputSchema, type MarketStateAgentInput } from './input.schema.js';
import { marketStateAssessmentSchema, type MarketStateAssessment } from './output.schema.js';

export const marketStateDefinition: AgentDefinition<MarketStateAgentInput, MarketStateAssessment> = {
  id: 'market-state',
  version: 'v1',
  promptVersion: 'market-state-v1',
  maxToolCalls: 0,
  outputSchema: marketStateAssessmentSchema,
  async invoke(untrustedInput) {
    const input = marketStateInputSchema.parse(untrustedInput);
    const snapshot = input.regimeSnapshot;
    const policy = {
      RISK_ON: { bias: 'NORMAL' as const, allow: true },
      NEUTRAL: { bias: 'NORMAL' as const, allow: true },
      RISK_OFF: { bias: 'CONSERVATIVE' as const, allow: false },
      STRESS: { bias: 'DEFENSIVE' as const, allow: false },
    }[snapshot.overallRegime];
    const highExposureRisk = input.portfolioExposure.grossExposure > 0.8 && !policy.allow;
    return {
      output: {
        assessmentId: `state-assessment:${snapshot.snapshotId}`,
        regimeSnapshotId: snapshot.snapshotId,
        interpretation: `当前市场状态为 ${snapshot.overallRegime}，仅依据已发布 MarketRegimeSnapshot 解释。`,
        suggestedRiskBias: policy.bias,
        allowNewPositions: policy.allow,
        preferredIndustries: [],
        avoidedIndustries: [],
        portfolioImplications: [
          `组合总暴露为 ${(input.portfolioExposure.grossExposure * 100).toFixed(1)}%。`,
          ...(highExposureRisk ? ['当前市场状态下组合暴露偏高，应提交独立风险复核。'] : []),
        ],
        risks: [
          ...(snapshot.changeDetected ? ['市场状态发生转换，历史假设可能不再适用。'] : []),
          ...(highExposureRisk ? ['高组合暴露与防御性市场状态不匹配。'] : []),
        ],
        evidenceIds: [...new Set([...snapshot.evidenceIds, ...input.portfolioExposure.evidenceIds])],
        confidence: snapshot.regimeConfidence,
        validUntil: input.decisionAsOf,
      },
      toolCalls: [],
    };
  },
};
