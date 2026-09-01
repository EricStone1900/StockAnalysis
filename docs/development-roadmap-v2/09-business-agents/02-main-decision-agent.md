# 09-02 主决策Agent

## 实施步骤

1. ContextBuilder确定性加载量化/策略、新闻、异常、Regime、Portfolio和专业评估。
2. 校验所有引用存在、ACTIVE、未过期、时间一致且内容Hash正确；缺失时不调用模型或标记证据不足。
3. Prompt要求比较支持与反对证据、策略冲突、成本、当前持仓、长期HOLD和失效条件。
4. 输出组合级TradeProposalDraft，顶层动作仅HOLD/REBALANCE；REBALANCE包含一个或多个BUY/SELL Leg，不包含Approval、预算预留、RebalanceBatch或Order。
5. HOLD也保存；每日检查不意味着每日交易。
6. 同一目标组合只能输出一个Proposal和稳定的targetPortfolioVersion，不得拆成多个单票Proposal规避批次或组合风险。

```ts
interface DecisionEvidenceBundle {
  decisionAsOf: string;
  quantSnapshotId: string;
  strategySnapshotIds: string[];
  newsEventIds: string[];
  anomalyEventIds: string[];
  marketRegimeSnapshotId: string;
  portfolioSnapshotId: string;
  specialistAssessmentRefs: string[];
  contextHash: string;
}
```

## 测试

- 策略分歧、NO_REBALANCE、连续HOLD和极端市场。
- CANDIDATE/过期策略不得进入上下文。
- 模型不得临时改Ensemble权重。
- Provider失败不产生可用BUY。
- HOLD的legs为空；多Leg REBALANCE与DailyStrategySnapshot目标组合一致，任一Leg缺少证据时不能形成可用Proposal。
- DAILY_TARGET、INTRADAY_RISK_REDUCTION和EXECUTION_CORRECTION reason符合触发来源；默认不生成第二批新Alpha建议。
