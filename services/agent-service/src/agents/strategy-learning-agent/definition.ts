import type { AgentDefinition } from '../../application/agent-kernel.js';
import { strategyLearningInputSchema, type StrategyLearningInput } from './input.schema.js';
import { strategyLearningDraftSchema, type StrategyLearningDraft } from './output.schema.js';

export const strategyLearningDefinition: AgentDefinition<StrategyLearningInput, StrategyLearningDraft> = {
  id: 'strategy-learning', version: 'v1', promptVersion: 'strategy-learning-v1', maxToolCalls: 0, outputSchema: strategyLearningDraftSchema,
  async invoke(untrustedInput) {
    const input = strategyLearningInputSchema.parse(untrustedInput);
    const supporting = input.outcomes.filter((outcome) => outcome.outcomeClass === 'SUCCESS').map((outcome) => outcome.decisionId);
    const counterexamples = input.outcomes.filter((outcome) => outcome.outcomeClass === 'COUNTEREXAMPLE').map((outcome) => outcome.decisionId);
    return {
      output: {
        title: `候选复盘：${input.currentStrategy.strategyId} ${input.currentStrategy.strategyVersion}`,
        hypothesis: '仅将当前策略在给定市场状态与评估窗口中的可重复表现提交为候选假设，不改变生产策略。',
        applicability: { regimes: ['UNSPECIFIED'], horizons: [5, 20, 60] },
        supportingDecisionIds: supporting,
        counterexampleDecisionIds: counterexamples,
        sampleBreakdown: Object.fromEntries([...new Set(input.outcomes.map((outcome) => outcome.episodeType))].map((type) => [type, input.outcomes.filter((outcome) => outcome.episodeType === type).length])),
        proposedExperiment: { strategyId: input.currentStrategy.strategyId, baseVersion: input.currentStrategy.strategyVersion, validation: ['PIT', 'WALK_FORWARD', 'COST', 'CAPACITY', 'REGIME'] },
        status: 'DRAFT',
      },
      toolCalls: [],
    };
  },
};
