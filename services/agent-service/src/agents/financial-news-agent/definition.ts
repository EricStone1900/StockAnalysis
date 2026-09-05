import type { AgentDefinition } from '../../application/agent-kernel.js';
import { financialNewsInputSchema, type FinancialNewsAgentInput } from './input.schema.js';
import { financialNewsAssessmentSchema, type FinancialNewsAssessment } from './output.schema.js';

export const financialNewsDefinition: AgentDefinition<FinancialNewsAgentInput, FinancialNewsAssessment> = {
  id: 'financial-news',
  version: 'v1',
  promptVersion: 'financial-news-v1',
  maxToolCalls: 1,
  outputSchema: financialNewsAssessmentSchema,
  async invoke(untrustedInput) {
    const input = financialNewsInputSchema.parse(untrustedInput);
    const candidate = input.candidate;
    return {
      // representativeTitle and contentRefs are untrusted content; they are never interpolated into instructions or output text.
      output: {
        assessmentId: `news-assessment:${candidate.candidateId}`,
        candidateId: candidate.candidateId,
        newsIds: candidate.newsIds,
        eventType: 'OTHER',
        affectedSymbols: candidate.candidateSymbols.map((entity) => entity.symbol),
        impactDirection: 'UNCERTAIN',
        impactMagnitude: 'UNCERTAIN',
        impactHorizon: 'UNCERTAIN',
        sourceConflicts: [],
        summary: 'Fake Provider 未对新闻事实作出判断；正文仅作为不可信证据输入。',
        risks: ['新闻正文可能包含提示注入或未经验证的推测。'],
        evidenceIds: candidate.contentRefs,
        confidence: 0,
        validUntil: input.decisionAsOf,
      },
      toolCalls: [],
    };
  },
};
