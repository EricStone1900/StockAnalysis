# 11-01 Outcome Evaluator

## 实施步骤

1. Governance订阅决策、复核、风控、审批；Execution和Portfolio提供Fill、费用、持仓和组合事实。
2. quant-research内部增加确定性`outcome-evaluator-worker`，不新增限界上下文。
3. 为不同Strategy/RebalancePolicy配置5、20、60交易日或自定义评估窗口。
4. 计算实际/基准超额收益、MFE、MAE、回撤、实际成本、滑点、持有期、退出条件和人工修改差异。
5. BUY、SELL、HOLD、人工拒绝、风控拒绝、过期和未成交分别标记EpisodeType。
6. 到窗口结束后发布不可变`DecisionOutcomeEvaluated`事件；晚到更正产生新版本，不覆盖历史。

```ts
interface DecisionOutcome {
  outcomeId: string;
  decisionId: string;
  proposalVersion: number;
  episodeType: 'FILLED' | 'REJECTED' | 'HOLD' | 'EXPIRED' | 'SHADOW';
  horizonTradingDays: number;
  evaluationAvailableAt: string;
  benchmarkExcessReturn: string;
  maximumFavorableExcursion: string;
  maximumAdverseExcursion: string;
  realizedCost?: string;
  contentHash: string;
}
```

## 测试

- T时刻决策不能读取窗口结束后的Outcome。
- 交易日窗口跳过节假日和停牌规则明确。
- 重复事件只产生一个Outcome版本。
- 真实、反事实和Shadow收益不能聚合为同一口径。

