import type { AgentDefinition } from '../../application/agent-kernel.js';
import { stockAnalysisInputSchema, type StockAnalysisAgentInput } from './input.schema.js';
import { stockAnalysisAssessmentSchema, type StockAnalysisAssessment } from './output.schema.js';

const unique = (values: readonly string[]): string[] => [...new Set(values)];

export const stockAnalysisDefinition: AgentDefinition<StockAnalysisAgentInput, StockAnalysisAssessment> = {
  id: 'stock-analysis',
  version: 'v1',
  promptVersion: 'stock-analysis-v1',
  maxToolCalls: 0,
  outputSchema: stockAnalysisAssessmentSchema,
  async invoke(untrustedInput) {
    const input = stockAnalysisInputSchema.parse(untrustedInput);
    const analysis = input.dailyAnalysisSnapshot.analyses.find((item) => item.symbol === input.symbol);
    if (!analysis) throw new Error('symbol must exist in DailyAnalysisSnapshot');

    const holding = input.portfolio.heldSymbols.includes(input.symbol);
    const supporting = input.activeStrategySnapshots
      .filter((snapshot) => snapshot.rebalanceDecision !== 'NO_REBALANCE')
      .map((snapshot) => snapshot.snapshotId);
    const noTrade = input.activeStrategySnapshots
      .filter((snapshot) => snapshot.rebalanceDecision === 'NO_REBALANCE')
      .map((snapshot) => snapshot.snapshotId);
    const conflict = supporting.length > 0 && noTrade.length > 0 ? noTrade : [];
    const baseline = supporting.length === 0
      ? (noTrade.length === 0 ? 'NOT_AVAILABLE' : 'SUPPORTS_HOLD')
      : (noTrade.length === 0 ? 'SUPPORTS_TRADE' : 'SUPPORTS_HOLD');
    const evidenceIds = unique([
      ...input.dailyAnalysisSnapshot.evidenceIds,
      ...analysis.evidenceIds,
      ...input.portfolio.evidenceIds,
      ...input.activeStrategySnapshots.flatMap((snapshot) => snapshot.evidenceIds),
    ]);

    return {
      output: {
        assessmentId: `stock-assessment:${input.dailyAnalysisSnapshot.snapshotId}:${input.symbol}`,
        stockAnalysisSnapshotId: input.dailyAnalysisSnapshot.snapshotId,
        symbol: input.symbol,
        summary: `${input.symbol} 的 ${analysis.signal} 信号仅基于已发布量化快照与 ACTIVE 策略快照解释。`,
        opportunities: analysis.signal === 'BUY' ? ['已发布快照显示正向候选信号。'] : [],
        risks: [
          ...(holding ? ['该股票已在组合中，需结合组合暴露判断。'] : []),
          ...(conflict.length > 0 ? ['ACTIVE 策略对再平衡存在冲突，不能自行选择策略。'] : []),
          ...(baseline === 'SUPPORTS_HOLD' ? ['NO_REBALANCE 基线支持持有，不构成必须交易的理由。'] : []),
        ],
        supportingStrategySnapshotIds: supporting,
        conflictingStrategySnapshotIds: conflict,
        noTradeBaseline: baseline,
        evidenceIds,
        confidence: conflict.length > 0 ? 0.5 : 0.8,
        validUntil: input.dailyAnalysisSnapshot.validUntil,
      },
      toolCalls: [],
    };
  },
};
