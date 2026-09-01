# Governance 05-01 骨架与Proposal最小切片

## 实施步骤

1. 建立Decision、组合级TradeProposal、RebalanceLeg和ProposalVersion Aggregate。
2. 最小Use Case为“接收结构化多Leg Fake建议，校验证据引用并创建DRAFT版本”。
3. Proposal不可覆盖更新；修改产生新proposalVersion和parentProposalVersion。
4. HOLD也保存，但legs必须为空且不进入审批和调仓批次；REBALANCE至少包含一个Leg。
5. 保存quant/strategy/news/regime/portfolio/anomaly快照引用、agentRunId和contentHash。
6. 保存targetPortfolioVersion和完整Leg集合Hash；禁止用多个单票Proposal表达同一目标组合。

```ts
type ProposalState =
  | 'DRAFT' | 'RISK_REVIEWED' | 'RISK_PASSED'
  | 'APPROVED' | 'REJECTED' | 'EXPIRED'
  | 'REVISION_REQUIRED' | 'REVIEW_BLOCKED';
```

## 测试

- 缺证据、过期快照和Hash错误拒绝。
- 相同Idempotency-Key只创建一个Decision。
- 修改不改变旧版本。
- HOLD不占组合调仓批次。
- 增删或修改任一Leg必须生成新proposalVersion，旧RiskReview和RiskEvaluation不可复用。
