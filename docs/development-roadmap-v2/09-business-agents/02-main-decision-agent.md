# 09-02 主决策Agent

## 实施步骤

1. ContextBuilder确定性加载量化/策略、新闻、异常、Regime、Portfolio和专业评估。
2. 校验所有引用存在、ACTIVE、未过期、时间一致且内容Hash正确；缺失时不调用模型或标记证据不足。
3. Prompt要求比较支持与反对证据、策略冲突、成本、当前持仓、长期HOLD和失效条件。
4. 输出结构化TradeProposalDraft，动作仅BUY/SELL/HOLD，不包含Approval或Order。
5. HOLD也保存；每日检查不意味着每日交易。

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

