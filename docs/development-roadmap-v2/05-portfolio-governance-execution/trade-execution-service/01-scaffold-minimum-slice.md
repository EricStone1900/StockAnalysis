# Execution 05-01 骨架与OrderIntent最小切片

## 实施步骤

1. 建立OrderIntent、Order、Fill和ExecutionBatch Aggregate。
2. 最小Use Case为“验证Fake批准引用并创建READY人工OrderIntent”。
3. 保存decisionId、proposalVersion、approvalId、riskEvaluationId、validUntil和contentHash。
4. 状态变更必须用命令，记录actor和原因；未知状态不自动重试创建。

```ts
type OrderIntentStatus =
  | 'DRAFT' | 'READY' | 'SUBMITTED_MANUALLY'
  | 'PARTIALLY_FILLED' | 'FILLED' | 'CANCELLED'
  | 'EXPIRED' | 'UNKNOWN';
```

## 测试

- 未批准、过期、旧版本或Risk失效不能创建READY。
- 重复命令不创建重复Intent。
- 非法状态跃迁拒绝。
- UNKNOWN不能自动重建订单。

