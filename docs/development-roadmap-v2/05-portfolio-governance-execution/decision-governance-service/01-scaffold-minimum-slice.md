# Governance 05-01 骨架与Proposal最小切片

## 实施步骤

1. 建立Decision、TradeProposal和ProposalVersion Aggregate。
2. 最小Use Case为“接收结构化Fake建议，校验证据引用并创建DRAFT版本”。
3. Proposal不可覆盖更新；修改产生新proposalVersion和parentProposalVersion。
4. HOLD也保存，但不进入审批和交易批次。
5. 保存quant/strategy/news/regime/portfolio/anomaly快照引用、agentRunId和contentHash。

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
- HOLD不占交易批次。

